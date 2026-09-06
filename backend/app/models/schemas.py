"""Pydantic request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class APIError(BaseModel):
    code: str
    message: str
    details: Any | None = None


class APIResponse(BaseModel):
    success: bool = True
    data: Any | None = None
    error: APIError | None = None
    meta: dict[str, Any] | None = None


class FeedbackCreate(BaseModel):
    feedback_id: str | None = Field(default=None, max_length=40)
    customer_id: str = Field(..., min_length=1, max_length=40)
    text: str = Field(..., min_length=3)
    date: datetime | None = None
    product: str = Field(..., min_length=1, max_length=120)
    department: str = Field(..., min_length=1, max_length=120)
    channel: str = Field(..., min_length=1, max_length=60)
    location: str = Field(..., min_length=1, max_length=80)
    segment: str = Field(..., min_length=1, max_length=60)
    rating: int = Field(..., ge=1, le=5)
    status: str = Field(default="open", max_length=40)


class FeedbackUpdate(BaseModel):
    text: str | None = None
    product: str | None = None
    department: str | None = None
    channel: str | None = None
    location: str | None = None
    segment: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    status: str | None = None


class BulkStatusUpdate(BaseModel):
    ids: list[int]
    status: str


class BulkDelete(BaseModel):
    ids: list[int]


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=3)
    rating: int | None = Field(default=None, ge=1, le=5)
    segment: str | None = None
    product: str | None = None
    department: str | None = None
    channel: str | None = None


class BulkAnalyzeRequest(BaseModel):
    ids: list[int] | None = None
    texts: list[str] | None = None


class AlertUpdate(BaseModel):
    status: str


class DatasetUploadMeta(BaseModel):
    name: str | None = None


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str
    database: str
    models: str
    timestamp: str
