"""Input and file validation helpers."""

from __future__ import annotations

from typing import Any

from backend.app.utils.helpers import CHANNEL_VALUES, safe_date

REQUIRED_CSV_COLUMNS = {
    "text",
    "date",
    "product",
    "department",
    "channel",
    "location",
    "segment",
    "rating",
}


class ValidationError(ValueError):
    def __init__(self, message: str, code: str = "VALIDATION_ERROR", details: Any = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details


def validate_rating(value: Any) -> int:
    try:
        rating = int(float(value))
    except (TypeError, ValueError) as exc:
        raise ValidationError("Rating must be an integer between 1 and 5.") from exc
    if rating < 1 or rating > 5:
        raise ValidationError("Rating must be between 1 and 5.")
    return rating


def validate_channel(value: str) -> str:
    channel = str(value).strip()
    if channel not in CHANNEL_VALUES:
        raise ValidationError(
            f"Unsupported channel '{channel}'.",
            details={"allowed": sorted(CHANNEL_VALUES)},
        )
    return channel


def validate_upload_filename(filename: str) -> None:
    if not filename.lower().endswith(".csv"):
        raise ValidationError("Only CSV files are supported.", code="INVALID_FILE_TYPE")


def validate_upload_size(size_bytes: int, max_mb: int) -> None:
    if size_bytes > max_mb * 1024 * 1024:
        raise ValidationError(
            f"File exceeds the {max_mb} MB upload limit.",
            code="FILE_TOO_LARGE",
        )


def validate_csv_columns(columns: list[str]) -> list[str]:
    normalized = [str(col).strip().lower() for col in columns]
    missing = sorted(REQUIRED_CSV_COLUMNS - set(normalized))
    if missing:
        raise ValidationError(
            "CSV is missing required columns.",
            details={"missing": missing, "required": sorted(REQUIRED_CSV_COLUMNS)},
        )
    return normalized


def validate_date_value(value: Any) -> None:
    if safe_date(value) is None:
        raise ValidationError(f"Invalid date value: {value}")
