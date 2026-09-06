"""CSV and JSON export helpers."""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.services import audit_service
from backend.app.services.feedback_service import apply_filters, serialize_feedback
from backend.app.models.database_models import Feedback
from backend.app.utils.helpers import utcnow


def _filtered_rows(db: Session, params: dict[str, Any]) -> list[Feedback]:
    query = apply_filters(db.query(Feedback), params).order_by(Feedback.date.desc())
    return query.limit(5000).all()


def _records(rows: list[Feedback]) -> list[dict[str, Any]]:
    payload = []
    for row in rows:
        item = serialize_feedback(row)
        analysis = item.get("analysis") or {}
        payload.append(
            {
                "feedback_id": item["feedback_id"],
                "customer_id": item["customer_id"],
                "date": item["date"],
                "text": item.get("text"),
                "product": item["product"],
                "department": item["department"],
                "channel": item["channel"],
                "location": item["location"],
                "segment": item["segment"],
                "rating": item["rating"],
                "status": item["status"],
                "sentiment": (analysis.get("sentiment") or {}).get("label"),
                "emotion": (analysis.get("emotion") or {}).get("label"),
                "category": analysis.get("category"),
                "intent": analysis.get("intent"),
                "priority": analysis.get("priority"),
                "severity": analysis.get("severity"),
            }
        )
    return payload


def export_json(db: Session, params: dict[str, Any], user: str, ip: str | None) -> tuple[bytes, str]:
    records = _records(_filtered_rows(db, params))
    raw = json.dumps({"count": len(records), "items": records}, indent=2).encode("utf-8")
    filename = f"insightai-export-{utcnow().strftime('%Y%m%d%H%M%S')}.json"
    path = get_settings().export_path / filename
    path.write_bytes(raw)
    audit_service.log_event(db, "EXPORT_GENERATED", user=user, ip=ip, metadata={"format": "json", "count": len(records)})
    return raw, filename


def export_csv(db: Session, params: dict[str, Any], user: str, ip: str | None) -> tuple[bytes, str]:
    records = _records(_filtered_rows(db, params))
    buffer = StringIO()
    fieldnames = [
        "feedback_id",
        "customer_id",
        "date",
        "text",
        "product",
        "department",
        "channel",
        "location",
        "segment",
        "rating",
        "status",
        "sentiment",
        "emotion",
        "category",
        "intent",
        "priority",
        "severity",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)
    raw = buffer.getvalue().encode("utf-8")
    filename = f"insightai-export-{utcnow().strftime('%Y%m%d%H%M%S')}.csv"
    path = get_settings().export_path / filename
    path.write_bytes(raw)
    audit_service.log_event(db, "EXPORT_GENERATED", user=user, ip=ip, metadata={"format": "csv", "count": len(records)})
    return raw, filename
