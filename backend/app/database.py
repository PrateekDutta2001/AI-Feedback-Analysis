"""SQLAlchemy engine, session factory, and database helpers."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _build_engine():
    settings = get_settings()
    connect_args = {}
    if settings.sqlalchemy_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(
        settings.sqlalchemy_url,
        connect_args=connect_args,
        future=True,
        pool_pre_ping=True,
    )

    if settings.sqlalchemy_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables."""
    from backend.app.models import database_models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def database_healthy() -> bool:
    """Return True when a simple database query succeeds."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
