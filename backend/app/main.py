"""InsightAI FastAPI application."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from backend.app.api import alerts, analytics, dashboard, datasets, exports, feedback, insights, models
from backend.app.config import get_settings
from backend.app.database import SessionLocal, database_healthy, init_db
from backend.app.ml.model_registry import store
from backend.app.ml.trainer import ensure_models
from backend.app.models.database_models import ModelRegistry
from backend.app.models.schemas import APIError, APIResponse
from backend.app.services.seed_service import seed_if_needed
from backend.app.utils.helpers import dump_json, utcnow
from backend.app.utils.logger import get_logger, setup_logging
from backend.app.utils.validators import ValidationError

setup_logging()
logger = get_logger("insightai")
settings = get_settings()

app = FastAPI(
    title="InsightAI",
    description="Enterprise Feedback Intelligence Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(feedback.router)
app.include_router(analytics.router)
app.include_router(insights.router)
app.include_router(alerts.router)
app.include_router(models.router)
app.include_router(datasets.router)
app.include_router(exports.router)

FRONTEND = settings.project_root / "frontend"


def _error(code: str, message: str, status_code: int, details=None) -> JSONResponse:
    payload = APIResponse(
        success=False,
        error=APIError(code=code, message=message, details=details),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


@app.exception_handler(ValidationError)
async def validation_handler(_request: Request, exc: ValidationError) -> JSONResponse:
    status = 404 if exc.code == "NOT_FOUND" else 400
    return _error(exc.code, exc.message, status, exc.details)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error("VALIDATION_ERROR", "Invalid request payload", 422, exc.errors())


@app.exception_handler(Exception)
async def unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled server error: %s", exc)
    return _error("INTERNAL_ERROR", "An unexpected error occurred. Please try again.", 500)


@app.get("/api/health", tags=["Health"], summary="Service health")
def health() -> dict:
    db_ok = database_healthy()
    models_ok = store.healthy()
    status = "healthy" if db_ok and models_ok else "degraded"
    return {
        "status": status,
        "database": "healthy" if db_ok else "unavailable",
        "models": "healthy" if models_ok else "unavailable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/settings", tags=["Settings"], summary="Public runtime settings")
def public_settings() -> APIResponse:
    return APIResponse(
        data={
            "app_name": settings.app_name,
            "app_env": settings.app_env,
            "similarity_threshold": settings.similarity_threshold,
            "max_upload_mb": settings.max_upload_mb,
        }
    )


def _register_initial_models(db: Session, trained: list[dict] | None) -> None:
    if db.query(ModelRegistry).count() > 0:
        return
    source = trained or list(store.metadata.values())
    for item in source:
        if not item:
            continue
        db.add(
            ModelRegistry(
                name=f"{str(item.get('name', 'model')).title()} Model",
                version=str(item.get("version", "1.0.0")),
                algorithm=str(item.get("algorithm", "TF-IDF + Logistic Regression")),
                training_date=utcnow(),
                dataset_size=int(item.get("dataset_size") or 0),
                accuracy=float(item.get("accuracy") or 0),
                precision=float(item.get("precision") or 0),
                recall=float(item.get("recall") or 0),
                f1=float(item.get("f1") or 0),
                status="active",
                metrics_json=dump_json(item),
            )
        )
    db.commit()


@app.on_event("startup")
def on_startup() -> None:
    logger.info("Starting %s", settings.app_name)
    init_db()
    db = SessionLocal()
    try:
        seed_if_needed(db)
        trained = ensure_models()
        from backend.app.services.alert_service import generate_alerts
        from backend.app.services.analytics_service import invalidate_cache
        from backend.app.services.seed_service import _analyze_existing

        _analyze_existing(db)
        generate_alerts(db)
        invalidate_cache()
        _register_initial_models(db, trained)
    finally:
        db.close()
    logger.info("InsightAI startup complete")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(FRONTEND / "index.html")


if FRONTEND.exists():
    for folder, name in (("css", "css"), ("js", "js"), ("assets", "assets")):
        target = FRONTEND / folder
        target.mkdir(parents=True, exist_ok=True)
        app.mount(f"/{name}", StaticFiles(directory=target), name=name)
