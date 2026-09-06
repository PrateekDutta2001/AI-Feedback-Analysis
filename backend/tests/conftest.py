"""Pytest fixtures using an isolated SQLite database."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(ROOT / 'insightai-test.db').as_posix()}")

import pytest
from fastapi.testclient import TestClient

from backend.app.config import get_settings
from backend.app.database import SessionLocal, init_db
from backend.app.ml.trainer import ensure_models
from backend.app.utils.data_generator import ensure_datasets


@pytest.fixture(scope="session")
def client():
    get_settings.cache_clear()
    ensure_datasets()
    init_db()
    ensure_models()
    from backend.app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db(client):
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
