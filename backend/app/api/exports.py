"""Export endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.app.api.deps import actor, client_ip, filter_params
from backend.app.database import get_db
from backend.app.services.export_service import export_csv, export_json

router = APIRouter(prefix="/api/export", tags=["Export"])


@router.get("/csv", summary="Export filtered feedback as CSV")
def csv_export(request: Request, db: Session = Depends(get_db)) -> Response:
    raw, filename = export_csv(db, filter_params(request), actor(request), client_ip(request))
    return Response(
        content=raw,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/json", summary="Export filtered feedback as JSON")
def json_export(request: Request, db: Session = Depends(get_db)) -> Response:
    raw, filename = export_json(db, filter_params(request), actor(request), client_ip(request))
    return Response(
        content=raw,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
