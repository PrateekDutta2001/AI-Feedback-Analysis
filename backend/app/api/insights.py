"""AI insights endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import filter_params
from backend.app.database import get_db
from backend.app.models.schemas import APIResponse
from backend.app.services.insight_service import collect_stats, generate_insights

router = APIRouter(prefix="/api/insights", tags=["Insights"])


@router.get(
    "",
    response_model=APIResponse,
    summary="Generated insights",
    description="Compute positive trends, negative trends, emerging issues, and recommendations from live data.",
)
def get_insights(request: Request, db: Session = Depends(get_db)) -> APIResponse:
    params = filter_params(request)
    return APIResponse(
        data={
            "insights": generate_insights(db, params),
            "stats": collect_stats(db, params),
        }
    )
