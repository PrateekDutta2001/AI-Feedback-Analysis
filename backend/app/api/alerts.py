"""Alert center endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import actor, client_ip, filter_params
from backend.app.database import get_db
from backend.app.models.schemas import APIResponse, AlertUpdate
from backend.app.services.alert_service import delete_alert, generate_alerts, list_alerts, serialize_alert, update_alert

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("", response_model=APIResponse, summary="List alerts")
def get_alerts(request: Request, db: Session = Depends(get_db)) -> APIResponse:
    rows, total = list_alerts(db, filter_params(request))
    unread = sum(1 for row in rows if row.status == "unread")
    return APIResponse(
        data=[serialize_alert(row) for row in rows],
        meta={"total": total, "unread": unread},
    )


@router.post("/refresh", response_model=APIResponse, summary="Recalculate alert rules")
def refresh_alerts(db: Session = Depends(get_db)) -> APIResponse:
    created = generate_alerts(db)
    return APIResponse(data={"created": len(created)})


@router.patch("/{alert_id}", response_model=APIResponse, summary="Update alert status")
def patch_alert(
    alert_id: int,
    payload: AlertUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> APIResponse:
    row = update_alert(db, alert_id, payload.status, actor(request), client_ip(request))
    return APIResponse(data=serialize_alert(row))


@router.delete("/{alert_id}", response_model=APIResponse, summary="Delete an alert")
def remove_alert(alert_id: int, request: Request, db: Session = Depends(get_db)) -> APIResponse:
    delete_alert(db, alert_id, actor(request), client_ip(request))
    return APIResponse(data={"deleted": alert_id})
