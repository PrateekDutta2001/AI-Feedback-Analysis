"""Feedback persistence, analysis, import, and query helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from backend.app.config import get_settings
from backend.app.ml.pipeline import analyze_text
from backend.app.ml.similarity import find_similar
from backend.app.models.database_models import Dataset, Feedback, FeedbackAnalysis
from backend.app.services import audit_service
from backend.app.utils.helpers import (
    dump_json,
    generate_customer_id,
    generate_feedback_id,
    parse_json,
    safe_date,
    utcnow,
)
from backend.app.utils.validators import (
    REQUIRED_CSV_COLUMNS,
    ValidationError,
    validate_channel,
    validate_csv_columns,
    validate_rating,
    validate_upload_filename,
    validate_upload_size,
)

ALLOWED_SORT = {
    "date": Feedback.date,
    "rating": Feedback.rating,
    "product": Feedback.product,
    "department": Feedback.department,
    "channel": Feedback.channel,
    "status": Feedback.status,
    "feedback_id": Feedback.feedback_id,
}


def serialize_analysis(analysis: FeedbackAnalysis | None) -> dict[str, Any] | None:
    if analysis is None:
        return None
    return {
        "sentiment": {
            "label": analysis.sentiment,
            "confidence": analysis.sentiment_score,
            "positive": analysis.sentiment_positive,
            "neutral": analysis.sentiment_neutral,
            "negative": analysis.sentiment_negative,
        },
        "emotion": {"label": analysis.emotion, "confidence": analysis.emotion_score},
        "category": analysis.category,
        "intent": analysis.intent,
        "priority": analysis.priority,
        "priority_score": analysis.priority_score,
        "priority_reasons": parse_json(analysis.priority_reasons, []),
        "severity": analysis.severity,
        "keywords": parse_json(analysis.keywords, []),
        "topics": parse_json(analysis.topics, []),
        "aspects": parse_json(analysis.aspects, []),
        "recommendation": analysis.recommendation,
        "explanation": parse_json(analysis.explanation, {}),
        "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
    }


def serialize_feedback(row: Feedback, include_text: bool = True) -> dict[str, Any]:
    payload = {
        "id": row.id,
        "feedback_id": row.feedback_id,
        "customer_id": row.customer_id,
        "date": row.date.isoformat() if row.date else None,
        "product": row.product,
        "department": row.department,
        "channel": row.channel,
        "location": row.location,
        "segment": row.segment,
        "rating": row.rating,
        "status": row.status,
        "is_duplicate": bool(row.is_duplicate),
        "duplicate_of_id": row.duplicate_of_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "analysis": serialize_analysis(row.analysis),
    }
    if include_text:
        payload["text"] = row.text
    return payload


def _similar_corpus(db: Session, exclude_id: int | None = None, limit: int = 250) -> list[dict[str, Any]]:
    query = db.query(Feedback).order_by(Feedback.date.desc())
    if exclude_id:
        query = query.filter(Feedback.id != exclude_id)
    rows = query.limit(limit).all()
    return [{"id": row.id, "feedback_id": row.feedback_id, "text": row.text} for row in rows]


def persist_analysis(
    db: Session,
    feedback: Feedback,
    result: dict[str, Any],
    commit: bool = True,
) -> FeedbackAnalysis:
    sentiment = result["sentiment"]
    emotion = result["emotion"]
    priority = result["priority"]
    severity = result["severity"]
    record = feedback.analysis or FeedbackAnalysis(feedback_pk=feedback.id)
    record.sentiment = sentiment["label"]
    record.sentiment_score = sentiment["score"]
    record.sentiment_positive = sentiment["positive"]
    record.sentiment_neutral = sentiment["neutral"]
    record.sentiment_negative = sentiment["negative"]
    record.emotion = emotion["emotion"]
    record.emotion_score = emotion["confidence"]
    record.category = result["category"]
    record.category_score = result.get("category_score", 0.0)
    record.intent = result["intent"]
    record.intent_score = result.get("intent_score", 0.0)
    record.priority = priority["priority"]
    record.priority_score = priority["score"]
    record.priority_reasons = dump_json(priority["reason"])
    record.severity = severity["severity"]
    record.keywords = dump_json(result.get("keywords", []))
    record.topics = dump_json(result.get("topics", []))
    record.aspects = dump_json(result.get("aspects", []))
    record.recommendation = result.get("recommendation", {}).get("action", "")
    record.explanation = dump_json(result.get("explanation", {}))
    record.analyzed_at = utcnow()
    if feedback.analysis is None:
        db.add(record)
        feedback.analysis = record
    similar = result.get("similar") or []
    if similar:
        feedback.is_duplicate = 1
        feedback.duplicate_of_id = similar[0].get("feedback_id")
    else:
        feedback.is_duplicate = 0
        feedback.duplicate_of_id = None
    if commit:
        db.commit()
        db.refresh(feedback)
    return record


def analyze_and_store(db: Session, feedback: Feedback) -> dict[str, Any]:
    repeat_count = (
        db.query(func.count(Feedback.id))
        .join(FeedbackAnalysis, FeedbackAnalysis.feedback_pk == Feedback.id)
        .filter(FeedbackAnalysis.category == (feedback.analysis.category if feedback.analysis else "Other"))
        .scalar()
        or 0
    )
    result = analyze_text(
        text=feedback.text,
        rating=feedback.rating,
        segment=feedback.segment,
        similar_corpus=_similar_corpus(db, exclude_id=feedback.id),
        repeat_count=int(repeat_count),
    )
    persist_analysis(db, feedback, result)
    return result


def create_feedback(db: Session, payload: dict[str, Any], user: str, ip: str | None) -> Feedback:
    feedback_id = payload.get("feedback_id") or generate_feedback_id()
    existing = db.query(Feedback).filter(Feedback.feedback_id == feedback_id).first()
    if existing:
        raise ValidationError("Feedback ID already exists.", code="DUPLICATE_FEEDBACK_ID")
    row = Feedback(
        feedback_id=feedback_id,
        customer_id=payload.get("customer_id") or generate_customer_id(),
        text=payload["text"].strip(),
        date=payload.get("date") or utcnow(),
        product=payload["product"],
        department=payload["department"],
        channel=validate_channel(payload["channel"]),
        location=payload["location"],
        segment=payload["segment"],
        rating=validate_rating(payload["rating"]),
        status=payload.get("status") or "open",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    analyze_and_store(db, row)
    audit_service.log_event(
        db,
        "FEEDBACK_CREATED",
        user=user,
        ip=ip,
        metadata={"feedback_id": row.feedback_id},
    )
    return db.query(Feedback).options(joinedload(Feedback.analysis)).filter(Feedback.id == row.id).one()


def update_feedback(db: Session, feedback_id: int, payload: dict[str, Any], user: str, ip: str | None) -> Feedback:
    row = db.query(Feedback).options(joinedload(Feedback.analysis)).filter(Feedback.id == feedback_id).first()
    if not row:
        raise ValidationError("Feedback not found.", code="NOT_FOUND")
    rerun = False
    for field in ("text", "product", "department", "channel", "location", "segment", "rating", "status"):
        if field in payload and payload[field] is not None:
            if field == "channel":
                setattr(row, field, validate_channel(payload[field]))
            elif field == "rating":
                setattr(row, field, validate_rating(payload[field]))
            else:
                setattr(row, field, payload[field])
            if field in {"text", "rating", "segment"}:
                rerun = True
    row.updated_at = utcnow()
    db.commit()
    if rerun:
        analyze_and_store(db, row)
    audit_service.log_event(db, "FEEDBACK_UPDATED", user=user, ip=ip, metadata={"id": feedback_id})
    return db.query(Feedback).options(joinedload(Feedback.analysis)).filter(Feedback.id == feedback_id).one()


def delete_feedback(db: Session, feedback_id: int, user: str, ip: str | None) -> None:
    row = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not row:
        raise ValidationError("Feedback not found.", code="NOT_FOUND")
    db.delete(row)
    db.commit()
    audit_service.log_event(db, "FEEDBACK_DELETED", user=user, ip=ip, metadata={"id": feedback_id})


def bulk_update_status(db: Session, ids: list[int], status: str, user: str, ip: str | None) -> int:
    rows = db.query(Feedback).filter(Feedback.id.in_(ids)).all()
    for row in rows:
        row.status = status
        row.updated_at = utcnow()
    db.commit()
    audit_service.log_event(
        db,
        "FEEDBACK_UPDATED",
        user=user,
        ip=ip,
        metadata={"ids": ids, "status": status, "bulk": True},
    )
    return len(rows)


def bulk_delete(db: Session, ids: list[int], user: str, ip: str | None) -> int:
    rows = db.query(Feedback).filter(Feedback.id.in_(ids)).all()
    for row in rows:
        db.delete(row)
    db.commit()
    audit_service.log_event(db, "FEEDBACK_DELETED", user=user, ip=ip, metadata={"ids": ids, "bulk": True})
    return len(rows)


def get_feedback(db: Session, feedback_id: int) -> Feedback:
    row = db.query(Feedback).options(joinedload(Feedback.analysis)).filter(Feedback.id == feedback_id).first()
    if not row:
        raise ValidationError("Feedback not found.", code="NOT_FOUND")
    return row


def apply_filters(query, params: dict[str, Any]):
    if params.get("q"):
        term = f"%{params['q'].strip()}%"
        query = query.filter(
            or_(
                Feedback.text.ilike(term),
                Feedback.feedback_id.ilike(term),
                Feedback.customer_id.ilike(term),
                Feedback.product.ilike(term),
            )
        )
    if params.get("product"):
        query = query.filter(Feedback.product == params["product"])
    if params.get("department"):
        query = query.filter(Feedback.department == params["department"])
    if params.get("channel"):
        query = query.filter(Feedback.channel == params["channel"])
    if params.get("location"):
        query = query.filter(Feedback.location == params["location"])
    if params.get("segment"):
        query = query.filter(Feedback.segment == params["segment"])
    if params.get("status"):
        query = query.filter(Feedback.status == params["status"])
    if params.get("date_from"):
        start = safe_date(params["date_from"])
        if start:
            query = query.filter(Feedback.date >= start)
    if params.get("date_to"):
        end = safe_date(params["date_to"])
        if end:
            query = query.filter(Feedback.date <= end)
    if params.get("sentiment"):
        query = query.join(FeedbackAnalysis, isouter=True).filter(FeedbackAnalysis.sentiment == params["sentiment"])
    elif params.get("category") or params.get("priority") or params.get("emotion") or params.get("intent"):
        query = query.join(FeedbackAnalysis, isouter=True)
    if params.get("category"):
        query = query.filter(FeedbackAnalysis.category == params["category"])
    if params.get("priority"):
        query = query.filter(FeedbackAnalysis.priority == params["priority"])
    if params.get("emotion"):
        query = query.filter(FeedbackAnalysis.emotion == params["emotion"])
    if params.get("intent"):
        query = query.filter(FeedbackAnalysis.intent == params["intent"])
    return query


def list_feedback(db: Session, params: dict[str, Any]) -> tuple[list[Feedback], int]:
    query = db.query(Feedback).options(joinedload(Feedback.analysis))
    query = apply_filters(query, params)
    total = query.count()
    sort_key = params.get("sort") or "date"
    sort_col = ALLOWED_SORT.get(sort_key, Feedback.date)
    if params.get("order") == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())
    page = max(int(params.get("page") or 1), 1)
    page_size = min(max(int(params.get("page_size") or 20), 1), 100)
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return rows, total


def preview_csv(filename: str, raw: bytes) -> dict[str, Any]:
    validate_upload_filename(filename)
    validate_upload_size(len(raw), get_settings().max_upload_mb)
    try:
        frame = pd.read_csv(pd.io.common.BytesIO(raw))
    except Exception as exc:
        raise ValidationError("Unable to parse CSV file.", details=str(exc)) from exc
    columns = [str(col).strip() for col in frame.columns]
    validate_csv_columns(columns)
    frame.columns = [str(col).strip().lower() for col in frame.columns]
    issues: list[str] = []
    missing = int(frame[list(REQUIRED_CSV_COLUMNS)].isna().sum().sum())
    if missing:
        issues.append(f"{missing} missing required values")
    duplicates = int(frame.duplicated().sum())
    if duplicates:
        issues.append(f"{duplicates} duplicate rows")
    invalid_dates = 0
    for value in frame["date"].tolist():
        if safe_date(value) is None:
            invalid_dates += 1
    if invalid_dates:
        issues.append(f"{invalid_dates} invalid dates")
    invalid_ratings = 0
    for value in frame["rating"].tolist():
        try:
            validate_rating(value)
        except ValidationError:
            invalid_ratings += 1
    if invalid_ratings:
        issues.append(f"{invalid_ratings} invalid ratings")
    preview = frame.head(8).fillna("").to_dict(orient="records")
    return {
        "columns": list(frame.columns),
        "row_count": int(len(frame)),
        "missing_values": missing,
        "duplicate_count": duplicates,
        "invalid_dates": invalid_dates,
        "invalid_ratings": invalid_ratings,
        "issues": issues,
        "preview": preview,
        "valid": invalid_dates == 0 and invalid_ratings == 0 and len(frame) > 0,
    }


def import_csv(db: Session, filename: str, raw: bytes, user: str, ip: str | None) -> dict[str, Any]:
    preview = preview_csv(filename, raw)
    frame = pd.read_csv(pd.io.common.BytesIO(raw))
    frame.columns = [str(col).strip().lower() for col in frame.columns]
    frame = frame.drop_duplicates()
    imported = 0
    skipped = 0
    for record in frame.to_dict(orient="records"):
        text = str(record.get("text") or "").strip()
        date_value = safe_date(record.get("date"))
        if not text or date_value is None:
            skipped += 1
            continue
        try:
            rating = validate_rating(record.get("rating"))
            channel = validate_channel(str(record.get("channel")))
        except ValidationError:
            skipped += 1
            continue
        feedback_id = str(record.get("feedback_id") or generate_feedback_id())
        if db.query(Feedback).filter(Feedback.feedback_id == feedback_id).first():
            feedback_id = generate_feedback_id()
        row = Feedback(
            feedback_id=feedback_id,
            customer_id=str(record.get("customer_id") or generate_customer_id()),
            text=text,
            date=date_value,
            product=str(record.get("product") or "Unknown"),
            department=str(record.get("department") or "Product"),
            channel=channel,
            location=str(record.get("location") or "Unknown"),
            segment=str(record.get("segment") or "Consumer"),
            rating=rating,
            status=str(record.get("status") or "open"),
        )
        db.add(row)
        db.flush()
        analyze_and_store(db, row)
        imported += 1
    dates = [safe_date(value) for value in frame["date"].tolist()]
    valid_dates = [value for value in dates if value]
    dataset = Dataset(
        name=filename,
        filename=filename,
        row_count=imported,
        missing_values=preview["missing_values"],
        duplicate_count=preview["duplicate_count"],
        date_min=min(valid_dates).date().isoformat() if valid_dates else None,
        date_max=max(valid_dates).date().isoformat() if valid_dates else None,
    )
    db.add(dataset)
    db.commit()
    audit_service.log_event(
        db,
        "CSV_IMPORTED",
        user=user,
        ip=ip,
        metadata={"filename": filename, "imported": imported, "skipped": skipped},
    )
    return {
        "imported": imported,
        "skipped": skipped,
        "dataset_id": dataset.id,
        "issues": preview["issues"],
    }


def analyze_only(payload: dict[str, Any], db: Session) -> dict[str, Any]:
    return analyze_text(
        text=payload["text"],
        rating=payload.get("rating"),
        segment=payload.get("segment"),
        similar_corpus=_similar_corpus(db),
    )


def bulk_analyze(db: Session, ids: list[int] | None, user: str, ip: str | None) -> int:
    query = db.query(Feedback)
    if ids:
        query = query.filter(Feedback.id.in_(ids))
    rows = query.all()
    for row in rows:
        analyze_and_store(db, row)
    audit_service.log_event(db, "USER_ACTION", user=user, ip=ip, metadata={"action": "bulk_analyze", "count": len(rows)})
    return len(rows)
