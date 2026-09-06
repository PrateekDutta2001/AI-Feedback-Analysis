"""Model registry and training endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import actor, client_ip
from backend.app.database import get_db
from backend.app.ml.model_registry import store
from backend.app.ml.trainer import train_all
from backend.app.models.database_models import ModelRegistry
from backend.app.models.schemas import APIResponse
from backend.app.services import audit_service
from backend.app.utils.helpers import dump_json, utcnow
from backend.app.utils.validators import ValidationError

router = APIRouter(prefix="/api/models", tags=["Models"])


def _sync_registry(db: Session, metrics: list[dict]) -> None:
    db.query(ModelRegistry).update({"status": "retired"})
    for item in metrics:
        db.add(
            ModelRegistry(
                name=item["name"].title() + " Model",
                version=item["version"],
                algorithm=item["algorithm"],
                training_date=utcnow(),
                dataset_size=item["dataset_size"],
                accuracy=item["accuracy"],
                precision=item["precision"],
                recall=item["recall"],
                f1=item["f1"],
                status="active",
                metrics_json=dump_json(item),
            )
        )
    db.commit()


def _rows_from_disk_or_db(db: Session) -> list[dict]:
    rows = (
        db.query(ModelRegistry)
        .filter(ModelRegistry.status == "active")
        .order_by(ModelRegistry.training_date.desc())
        .all()
    )
    if rows:
        return [
            {
                "id": row.id,
                "name": row.name,
                "version": row.version,
                "algorithm": row.algorithm,
                "training_date": row.training_date.isoformat() if row.training_date else None,
                "dataset_size": row.dataset_size,
                "accuracy": row.accuracy,
                "precision": row.precision,
                "recall": row.recall,
                "f1": row.f1,
                "status": row.status,
                "metrics": json.loads(row.metrics_json or "{}"),
            }
            for row in rows
        ]
    payload = []
    for key, metadata in store.metadata.items():
        payload.append(
            {
                "name": f"{key.title()} Model",
                "version": metadata.get("version"),
                "algorithm": metadata.get("algorithm"),
                "training_date": metadata.get("training_date"),
                "dataset_size": metadata.get("dataset_size"),
                "accuracy": metadata.get("accuracy"),
                "precision": metadata.get("precision"),
                "recall": metadata.get("recall"),
                "f1": metadata.get("f1"),
                "status": metadata.get("status", "active"),
                "metrics": metadata,
            }
        )
    return payload


@router.get("", response_model=APIResponse, summary="List registered models")
def list_models(db: Session = Depends(get_db)) -> APIResponse:
    store.load_all()
    return APIResponse(data=_rows_from_disk_or_db(db))


@router.post("/train", response_model=APIResponse, summary="Retrain all models")
def train_models(request: Request, db: Session = Depends(get_db)) -> APIResponse:
    results = train_all()
    _sync_registry(db, results)
    audit_service.log_event(
        db,
        "MODEL_RETRAINED",
        user=actor(request),
        ip=client_ip(request),
        metadata={"models": [item["name"] for item in results]},
    )
    return APIResponse(data=results)


@router.get("/{model_name}", response_model=APIResponse, summary="Model detail and evaluation")
def get_model(model_name: str, db: Session = Depends(get_db)) -> APIResponse:
    normalized = model_name.lower().replace(" model", "").strip()
    rows = _rows_from_disk_or_db(db)
    match = next((row for row in rows if normalized in row["name"].lower()), None)
    if not match:
        raise ValidationError("Model not found.", code="NOT_FOUND")
    return APIResponse(data=match)
