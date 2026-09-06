"""Feedback ingestion, exploration, and analysis endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from backend.app.api.deps import actor, client_ip, filter_params
from backend.app.database import get_db
from backend.app.models.schemas import (
    APIResponse,
    AnalyzeRequest,
    BulkAnalyzeRequest,
    BulkDelete,
    BulkStatusUpdate,
    FeedbackCreate,
    FeedbackUpdate,
)
from backend.app.services.analytics_service import invalidate_cache
from backend.app.services.alert_service import generate_alerts
from backend.app.services.feedback_service import (
    analyze_only,
    bulk_analyze,
    bulk_delete,
    bulk_update_status,
    create_feedback,
    delete_feedback,
    get_feedback,
    import_csv,
    list_feedback,
    preview_csv,
    serialize_feedback,
    update_feedback,
)
from backend.app.ml.similarity import find_similar
from backend.app.models.database_models import Feedback

router = APIRouter(tags=["Feedback"])


@router.get(
    "/api/feedback",
    response_model=APIResponse,
    summary="List feedback",
    description="Search, filter, sort, and paginate feedback records.",
)
def list_items(request: Request, db: Session = Depends(get_db)) -> APIResponse:
    params = filter_params(request)
    rows, total = list_feedback(db, params)
    page = int(params.get("page") or 1)
    page_size = int(params.get("page_size") or 20)
    return APIResponse(
        data=[serialize_feedback(row) for row in rows],
        meta={"total": total, "page": page, "page_size": page_size},
    )


@router.post(
    "/api/feedback",
    response_model=APIResponse,
    summary="Create feedback",
    description="Create a feedback record and run the ML pipeline automatically.",
    status_code=201,
)
def create_item(payload: FeedbackCreate, request: Request, db: Session = Depends(get_db)) -> APIResponse:
    row = create_feedback(db, payload.model_dump(), actor(request), client_ip(request))
    invalidate_cache()
    generate_alerts(db)
    return APIResponse(data=serialize_feedback(row))


@router.get(
    "/api/feedback/{feedback_id}",
    response_model=APIResponse,
    summary="Get feedback detail",
    description="Return original text, analysis, explanation, similar records, and recommended action.",
)
def get_item(feedback_id: int, db: Session = Depends(get_db)) -> APIResponse:
    row = get_feedback(db, feedback_id)
    payload = serialize_feedback(row)
    corpus = [
        {"id": item.id, "feedback_id": item.feedback_id, "text": item.text}
        for item in db.query(Feedback).filter(Feedback.id != row.id).order_by(Feedback.date.desc()).limit(250)
    ]
    payload["similar"] = find_similar(row.text, corpus)
    return APIResponse(data=payload)


@router.patch(
    "/api/feedback/{feedback_id}",
    response_model=APIResponse,
    summary="Update feedback",
)
def patch_item(
    feedback_id: int,
    payload: FeedbackUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> APIResponse:
    row = update_feedback(
        db,
        feedback_id,
        payload.model_dump(exclude_unset=True),
        actor(request),
        client_ip(request),
    )
    invalidate_cache()
    return APIResponse(data=serialize_feedback(row))


@router.delete(
    "/api/feedback/{feedback_id}",
    response_model=APIResponse,
    summary="Delete feedback",
)
def remove_item(feedback_id: int, request: Request, db: Session = Depends(get_db)) -> APIResponse:
    delete_feedback(db, feedback_id, actor(request), client_ip(request))
    invalidate_cache()
    return APIResponse(data={"deleted": feedback_id})


@router.post(
    "/api/feedback/analyze",
    response_model=APIResponse,
    summary="Analyze text without saving",
    description="Run the full ML pipeline on arbitrary text.",
)
def analyze_item(payload: AnalyzeRequest, db: Session = Depends(get_db)) -> APIResponse:
    result = analyze_only(payload.model_dump(), db)
    return APIResponse(data=result)


@router.post(
    "/api/feedback/bulk-analyze",
    response_model=APIResponse,
    summary="Bulk analyze stored feedback",
)
def bulk_analyze_items(
    payload: BulkAnalyzeRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> APIResponse:
    count = bulk_analyze(db, payload.ids, actor(request), client_ip(request))
    invalidate_cache()
    return APIResponse(data={"analyzed": count})


@router.post(
    "/api/feedback/bulk-status",
    response_model=APIResponse,
    summary="Bulk status change",
)
def bulk_status(payload: BulkStatusUpdate, request: Request, db: Session = Depends(get_db)) -> APIResponse:
    count = bulk_update_status(db, payload.ids, payload.status, actor(request), client_ip(request))
    invalidate_cache()
    return APIResponse(data={"updated": count})


@router.post(
    "/api/feedback/bulk-delete",
    response_model=APIResponse,
    summary="Bulk delete",
)
def bulk_remove(payload: BulkDelete, request: Request, db: Session = Depends(get_db)) -> APIResponse:
    count = bulk_delete(db, payload.ids, actor(request), client_ip(request))
    invalidate_cache()
    return APIResponse(data={"deleted": count})


@router.post(
    "/api/upload",
    response_model=APIResponse,
    summary="Preview a CSV upload",
    description="Validate file type, columns, missing values, duplicates, dates, and ratings.",
)
async def upload_preview(file: UploadFile = File(...)) -> APIResponse:
    raw = await file.read()
    return APIResponse(data=preview_csv(file.filename or "upload.csv", raw))


@router.post(
    "/api/import",
    response_model=APIResponse,
    summary="Import a validated CSV",
    description="Normalize rows, store records, run the ML pipeline, and register the dataset.",
)
async def import_file(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> APIResponse:
    raw = await file.read()
    result = import_csv(db, file.filename or "upload.csv", raw, actor(request), client_ip(request))
    invalidate_cache()
    generate_alerts(db)
    return APIResponse(data=result)
