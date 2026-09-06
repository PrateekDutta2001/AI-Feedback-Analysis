"""Dataset management and audit log endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import actor, client_ip, filter_params
from backend.app.database import get_db
from backend.app.models.database_models import Dataset
from backend.app.models.schemas import APIResponse
from backend.app.services import audit_service
from backend.app.utils.helpers import parse_json
from backend.app.utils.validators import ValidationError

router = APIRouter(tags=["Data Management"])


@router.get("/api/datasets", response_model=APIResponse, summary="List uploaded datasets")
def list_datasets(db: Session = Depends(get_db)) -> APIResponse:
    rows = db.query(Dataset).order_by(Dataset.created_at.desc()).all()
    return APIResponse(
        data=[
            {
                "id": row.id,
                "name": row.name,
                "filename": row.filename,
                "row_count": row.row_count,
                "missing_values": row.missing_values,
                "duplicate_count": row.duplicate_count,
                "date_min": row.date_min,
                "date_max": row.date_max,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    )


@router.delete("/api/datasets/{dataset_id}", response_model=APIResponse, summary="Delete a dataset record")
def delete_dataset(dataset_id: int, request: Request, db: Session = Depends(get_db)) -> APIResponse:
    row = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not row:
        raise ValidationError("Dataset not found.", code="NOT_FOUND")
    db.delete(row)
    db.commit()
    audit_service.log_event(
        db,
        "USER_ACTION",
        user=actor(request),
        ip=client_ip(request),
        metadata={"action": "dataset_deleted", "id": dataset_id},
    )
    return APIResponse(data={"deleted": dataset_id})


@router.get("/api/audit", response_model=APIResponse, summary="Audit log trail")
def list_audit(request: Request, db: Session = Depends(get_db)) -> APIResponse:
    params = filter_params(request)
    rows, total = audit_service.list_audit_logs(
        db,
        event=params.get("type"),
        limit=int(params.get("page_size") or 50),
        offset=(max(int(params.get("page") or 1), 1) - 1) * int(params.get("page_size") or 50),
    )
    return APIResponse(
        data=[
            {
                "id": row.id,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "event": row.event,
                "user": row.user,
                "ip": row.ip,
                "metadata": parse_json(row.metadata_json, {}),
            }
            for row in rows
        ],
        meta={"total": total},
    )
