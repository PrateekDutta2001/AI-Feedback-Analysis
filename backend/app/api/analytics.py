"""Analytics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import filter_params
from backend.app.database import get_db
from backend.app.models.schemas import APIResponse
from backend.app.services.analytics_service import (
    aspect_summary,
    dashboard,
    department_performance,
    lookup_values,
    product_performance,
    topics,
    trends,
)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/sentiment", response_model=APIResponse, summary="Sentiment distribution and trend")
def sentiment_analytics(request: Request, db: Session = Depends(get_db)) -> APIResponse:
    params = filter_params(request)
    charts = dashboard(db, params)["charts"]
    return APIResponse(
        data={
            "distribution": charts["sentiment_distribution"],
            "trend": charts["sentiment_trend"],
            "lookups": lookup_values(db),
        }
    )


@router.get("/trends", response_model=APIResponse, summary="Multi-metric trend series")
def trend_analytics(request: Request, db: Session = Depends(get_db)) -> APIResponse:
    return APIResponse(data=trends(db, filter_params(request)))


@router.get("/categories", response_model=APIResponse, summary="Category breakdown")
def category_analytics(request: Request, db: Session = Depends(get_db)) -> APIResponse:
    charts = dashboard(db, filter_params(request))["charts"]
    return APIResponse(data=charts["category"])


@router.get("/emotions", response_model=APIResponse, summary="Emotion breakdown")
def emotion_analytics(request: Request, db: Session = Depends(get_db)) -> APIResponse:
    charts = dashboard(db, filter_params(request))["charts"]
    return APIResponse(data=charts["emotion"])


@router.get("/departments", response_model=APIResponse, summary="Department performance ranking")
def department_analytics(request: Request, db: Session = Depends(get_db)) -> APIResponse:
    return APIResponse(data=department_performance(db, filter_params(request)))


@router.get("/products", response_model=APIResponse, summary="Product and service analytics")
def product_analytics(request: Request, db: Session = Depends(get_db)) -> APIResponse:
    return APIResponse(data=product_performance(db, filter_params(request)))


@router.get("/topics", response_model=APIResponse, summary="Discovered topics")
def topic_analytics(request: Request, db: Session = Depends(get_db)) -> APIResponse:
    return APIResponse(data=topics(db, filter_params(request)))


@router.get("/aspects", response_model=APIResponse, summary="Aspect-level sentiment")
def aspect_analytics(request: Request, db: Session = Depends(get_db)) -> APIResponse:
    return APIResponse(data=aspect_summary(db, filter_params(request)))
