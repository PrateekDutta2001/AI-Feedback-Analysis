"""Persist audit events to the database and log files."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.database_models import AuditLog
from backend.app.utils.helpers import dump_json, utcnow
from backend.app.utils.logger import write_audit_file


def log_event(
    db: Session,
    event: str,
    user: str = "system",
    ip: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    payload = metadata or {}
    record = AuditLog(
        timestamp=utcnow(),
        event=event,
        user=user,
        ip=ip,
        metadata_json=dump_json(payload),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    write_audit_file(event, user, ip, payload)
    return record


def list_audit_logs(
    db: Session,
    event: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    query = db.query(AuditLog)
    if event:
        query = query.filter(AuditLog.event == event)
    total = query.count()
    rows = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()
    return rows, total
