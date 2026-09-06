"""Reusable helper functions."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

CHANNEL_VALUES = {
    "Website",
    "Mobile App",
    "Email",
    "Call Center",
    "Social Media",
    "Survey",
    "Chat",
    "Internal",
}

DEPARTMENT_VALUES = {
    "Customer Support",
    "Operations",
    "Product",
    "Engineering",
    "Sales",
    "Finance",
    "HR",
}

STATUS_VALUES = {"open", "in_progress", "resolved", "closed"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_feedback_id() -> str:
    return f"FB-{uuid.uuid4().hex[:8].upper()}"


def generate_alert_id() -> str:
    return f"AL-{uuid.uuid4().hex[:8].upper()}"


def generate_customer_id() -> str:
    return f"CU-{uuid.uuid4().hex[:8].upper()}"


def parse_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def dump_json(value: Any) -> str:
    return json.dumps(value, default=str)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def percent(part: float, whole: float) -> float:
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100, 2)


def delta_percent(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 2)


def normalize_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def safe_date(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            parsed = datetime.strptime(text[:19], fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def truncate(text: str, length: int = 140) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= length:
        return cleaned
    return cleaned[: length - 1].rstrip() + "…"
