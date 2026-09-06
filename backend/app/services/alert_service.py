"""Rule-based alert generation and management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.database_models import Alert, Feedback, FeedbackAnalysis
from backend.app.services import audit_service
from backend.app.services.insight_service import collect_stats
from backend.app.utils.helpers import generate_alert_id, utcnow
from backend.app.utils.validators import ValidationError


def serialize_alert(row: Alert) -> dict[str, Any]:
    return {
        "id": row.id,
        "alert_id": row.alert_id,
        "type": row.type,
        "severity": row.severity,
        "message": row.message,
        "feedback_id": row.feedback_id,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
    }


def _exists(db: Session, alert_type: str, message: str) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    return (
        db.query(Alert)
        .filter(Alert.type == alert_type, Alert.message == message, Alert.created_at >= cutoff)
        .first()
        is not None
    )


def _create(db: Session, alert_type: str, severity: str, message: str, feedback_id: str | None = None) -> Alert | None:
    if _exists(db, alert_type, message):
        return None
    row = Alert(
        alert_id=generate_alert_id(),
        type=alert_type,
        severity=severity,
        message=message,
        feedback_id=feedback_id,
        status="unread",
        created_at=utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def generate_alerts(db: Session) -> list[Alert]:
    created: list[Alert] = []
    critical_rows = (
        db.query(Feedback, FeedbackAnalysis)
        .join(FeedbackAnalysis)
        .filter(FeedbackAnalysis.priority == "critical", Feedback.status.in_(["open", "in_progress"]))
        .order_by(Feedback.date.desc())
        .limit(8)
        .all()
    )
    for feedback, _analysis in critical_rows:
        row = _create(
            db,
            "critical_feedback",
            "critical",
            f"Critical feedback {feedback.feedback_id} requires attention: {feedback.text[:140]}",
            feedback.feedback_id,
        )
        if row:
            created.append(row)

    stats = collect_stats(db)
    spike = (stats.get("sentiment_delta") or {}).get("negative")
    if spike and spike >= 8:
        row = _create(
            db,
            "negative_sentiment_spike",
            "high",
            f"Negative sentiment increased by {spike:.1f}% versus the previous period.",
        )
        if row:
            created.append(row)

    if stats.get("emerging_term"):
        item = stats["emerging_term"]
        row = _create(
            db,
            "new_emerging_topic",
            "high",
            f"Emerging topic '{item['term']}' increased to {item['recent']} mentions in {item['window']} days.",
        )
        if row:
            created.append(row)

    rating_delta = stats.get("rating_delta")
    if rating_delta is not None and rating_delta <= -0.25:
        row = _create(
            db,
            "rating_drop",
            "high",
            f"Average rating dropped by {abs(rating_delta):.2f} points versus the previous period.",
        )
        if row:
            created.append(row)

    duplicate_count = db.query(Feedback).filter(Feedback.is_duplicate == 1).count()
    if duplicate_count >= 5:
        row = _create(
            db,
            "duplicate_feedback_spike",
            "medium",
            f"{duplicate_count} near-duplicate feedback records are currently flagged.",
        )
        if row:
            created.append(row)

    if stats.get("top_negative_category"):
        item = stats["top_negative_category"]
        if item["count"] >= 12:
            row = _create(
                db,
                "high_volume_issue",
                "high",
                f"High-volume issue in {item['category']}: {item['count']} negative records ({item['share']:.1f}%).",
            )
            if row:
                created.append(row)
    return created


def list_alerts(db: Session, params: dict[str, Any]) -> tuple[list[Alert], int]:
    query = db.query(Alert)
    if params.get("status"):
        query = query.filter(Alert.status == params["status"])
    if params.get("type"):
        query = query.filter(Alert.type == params["type"])
    if params.get("severity"):
        query = query.filter(Alert.severity == params["severity"])
    total = query.count()
    page = max(int(params.get("page") or 1), 1)
    page_size = min(max(int(params.get("page_size") or 20), 1), 100)
    rows = query.order_by(Alert.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return rows, total


def update_alert(db: Session, alert_pk: int, status: str, user: str, ip: str | None) -> Alert:
    row = db.query(Alert).filter(Alert.id == alert_pk).first()
    if not row:
        raise ValidationError("Alert not found.", code="NOT_FOUND")
    if status not in {"unread", "read", "resolved"}:
        raise ValidationError("Unsupported alert status.")
    row.status = status
    row.resolved_at = utcnow() if status == "resolved" else None
    db.commit()
    db.refresh(row)
    if status == "resolved":
        audit_service.log_event(db, "ALERT_RESOLVED", user=user, ip=ip, metadata={"alert_id": row.alert_id})
    else:
        audit_service.log_event(db, "USER_ACTION", user=user, ip=ip, metadata={"alert_id": row.alert_id, "status": status})
    return row


def delete_alert(db: Session, alert_pk: int, user: str, ip: str | None) -> None:
    row = db.query(Alert).filter(Alert.id == alert_pk).first()
    if not row:
        raise ValidationError("Alert not found.", code="NOT_FOUND")
    db.delete(row)
    db.commit()
    audit_service.log_event(db, "USER_ACTION", user=user, ip=ip, metadata={"action": "alert_deleted", "id": alert_pk})
