"""SQLAlchemy ORM models for InsightAI."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(60), default="analyst")
    email: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        UniqueConstraint("feedback_id", name="uq_feedback_feedback_id"),
        Index("ix_feedback_date", "date"),
        Index("ix_feedback_product", "product"),
        Index("ix_feedback_department", "department"),
        Index("ix_feedback_channel", "channel"),
        Index("ix_feedback_status", "status"),
        Index("ix_feedback_location", "location"),
        Index("ix_feedback_segment", "segment"),
        Index("ix_feedback_rating", "rating"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feedback_id: Mapped[str] = mapped_column(String(40), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    product: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str] = mapped_column(String(120), nullable=False)
    channel: Mapped[str] = mapped_column(String(60), nullable=False)
    location: Mapped[str] = mapped_column(String(80), nullable=False)
    segment: Mapped[str] = mapped_column(String(60), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="open")
    is_duplicate: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_of_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    analysis: Mapped["FeedbackAnalysis | None"] = relationship(
        back_populates="feedback",
        uselist=False,
        cascade="all, delete-orphan",
    )


class FeedbackAnalysis(Base):
    __tablename__ = "feedback_analysis"
    __table_args__ = (
        Index("ix_analysis_sentiment", "sentiment"),
        Index("ix_analysis_category", "category"),
        Index("ix_analysis_priority", "priority"),
        Index("ix_analysis_emotion", "emotion"),
        Index("ix_analysis_intent", "intent"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feedback_pk: Mapped[int] = mapped_column(
        ForeignKey("feedback.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    sentiment_positive: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_neutral: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_negative: Mapped[float] = mapped_column(Float, default=0.0)
    emotion: Mapped[str] = mapped_column(String(40), nullable=False)
    emotion_score: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    category_score: Mapped[float] = mapped_column(Float, default=0.0)
    intent: Mapped[str] = mapped_column(String(60), nullable=False)
    intent_score: Mapped[float] = mapped_column(Float, default=0.0)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    priority_reasons: Mapped[str] = mapped_column(Text, default="[]")
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    keywords: Mapped[str] = mapped_column(Text, default="[]")
    topics: Mapped[str] = mapped_column(Text, default="[]")
    aspects: Mapped[str] = mapped_column(Text, default="[]")
    recommendation: Mapped[str] = mapped_column(Text, default="")
    explanation: Mapped[str] = mapped_column(Text, default="{}")
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    feedback: Mapped[Feedback] = relationship(back_populates="analysis")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_type", "type"),
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_severity", "severity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="unread")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    missing_values: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    date_min: Mapped[str | None] = mapped_column(String(40), nullable=True)
    date_max: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelRegistry(Base):
    __tablename__ = "model_registry"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_model_name_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(120), nullable=False)
    training_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    dataset_size: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    precision: Mapped[float] = mapped_column(Float, default=0.0)
    recall: Mapped[float] = mapped_column(Float, default=0.0)
    f1: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_event", "event"),
        Index("ix_audit_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    event: Mapped[str] = mapped_column(String(80), nullable=False)
    user: Mapped[str] = mapped_column(String(80), default="system")
    ip: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
