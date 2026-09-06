"""Dashboard KPI and chart endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import filter_params
from backend.app.database import get_db
from backend.app.models.schemas import APIResponse
from backend.app.services.analytics_service import dashboard, lookup_values
from backend.app.services.insight_service import generate_insights

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get(
    "",
    response_model=APIResponse,
    summary="Dashboard KPIs and charts",
    description="Return KPI cards, chart series, and dynamically generated AI insights.",
)
def get_dashboard(request: Request, db: Session = Depends(get_db)) -> APIResponse:
    params = filter_params(request)
    payload = dashboard(db, params)
    payload["insights"] = generate_insights(db, params)
    payload["lookups"] = lookup_values(db)
    return APIResponse(data=payload)
