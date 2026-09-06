"""Shared request helpers."""

from __future__ import annotations

from fastapi import Request

from backend.app.config import get_settings


def actor(request: Request) -> str:
    return request.headers.get("X-User") or get_settings().default_user


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def filter_params(request: Request) -> dict:
    keys = (
        "q",
        "product",
        "department",
        "channel",
        "location",
        "segment",
        "status",
        "sentiment",
        "category",
        "priority",
        "emotion",
        "intent",
        "date_from",
        "date_to",
        "sort",
        "order",
        "page",
        "page_size",
        "type",
        "severity",
    )
    return {key: request.query_params.get(key) for key in keys if request.query_params.get(key)}
