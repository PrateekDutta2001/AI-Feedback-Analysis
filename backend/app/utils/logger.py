"""Application, error, and audit logging with rotation."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from backend.app.config import get_settings

_INITIALIZED = False


def setup_logging() -> None:
    """Configure rotating file and console loggers once."""
    global _INITIALIZED
    if _INITIALIZED:
        return

    settings = get_settings()
    log_dir: Path = settings.log_path
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    app_handler = RotatingFileHandler(
        log_dir / "app.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    app_handler.setFormatter(formatter)

    error_handler = RotatingFileHandler(
        log_dir / "error.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(app_handler)
    root.addHandler(error_handler)
    root.addHandler(console)

    audit_logger = logging.getLogger("insightai.audit")
    audit_handler = RotatingFileHandler(
        log_dir / "audit.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    audit_handler.setFormatter(formatter)
    audit_logger.handlers.clear()
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False

    _INITIALIZED = True


def get_logger(name: str = "insightai") -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)


def write_audit_file(event: str, user: str, ip: str | None, metadata: dict[str, Any]) -> None:
    logger = logging.getLogger("insightai.audit")
    payload = json.dumps(
        {"event": event, "user": user, "ip": ip, "metadata": metadata},
        default=str,
    )
    logger.info(payload)
