"""First-run database seeding from dummy datasets."""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.ml.pipeline import analyze_text
from backend.app.models.database_models import Dataset, Department, Feedback, Product, User
from backend.app.services.feedback_service import persist_analysis
from backend.app.utils.data_generator import ensure_datasets
from backend.app.utils.helpers import safe_date
from backend.app.utils.logger import get_logger

logger = get_logger("insightai.seed")

PRODUCT_DESCRIPTIONS = {
    "InsightPay": "Payments and checkout platform",
    "InsightCloud": "Cloud workspace suite",
    "InsightMobile": "Mobile companion application",
    "InsightCRM": "Customer relationship management",
    "InsightAnalytics": "Analytics and reporting suite",
    "InsightSecure": "Identity and security controls",
    "InsightChat": "In-app messaging",
    "InsightPortal": "Customer self-service portal",
}


def _ensure_reference_data(db: Session) -> None:
    if db.query(Product).count() == 0:
        for name, description in PRODUCT_DESCRIPTIONS.items():
            db.add(Product(name=name, description=description))
    if db.query(Department).count() == 0:
        for name in [
            "Customer Support",
            "Operations",
            "Product",
            "Engineering",
            "Sales",
            "Finance",
            "HR",
        ]:
            db.add(Department(name=name, description=f"{name} organization"))
    if db.query(User).count() == 0:
        db.add(
            User(
                username="analyst",
                display_name="Priya Shah",
                role="analyst",
                email="priya.shah@insightai.local",
            )
        )
        db.add(
            User(
                username="admin",
                display_name="Alex Morgan",
                role="admin",
                email="alex.morgan@insightai.local",
            )
        )
    db.commit()


def _import_dummy(db: Session, path: Path) -> int:
    imported = 0
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        batch: list[Feedback] = []
        for record in reader:
            date_value = safe_date(record.get("date"))
            if not record.get("text") or date_value is None:
                continue
            batch.append(
                Feedback(
                    feedback_id=record.get("feedback_id") or f"FB-SEED-{imported + 1}",
                    customer_id=record.get("customer_id") or "CU-0000",
                    text=record["text"].strip(),
                    date=date_value,
                    product=record.get("product") or "InsightPortal",
                    department=record.get("department") or "Product",
                    channel=record.get("channel") or "Website",
                    location=record.get("location") or "Mumbai",
                    segment=record.get("segment") or "Consumer",
                    rating=int(float(record.get("rating") or 3)),
                    status=record.get("status") or "open",
                )
            )
            if len(batch) >= 250:
                db.add_all(batch)
                db.commit()
                imported += len(batch)
                batch = []
        if batch:
            db.add_all(batch)
            db.commit()
            imported += len(batch)
    return imported


def _analyze_existing(db: Session) -> int:
    rows = db.query(Feedback).all()
    analyzed = 0
    for row in rows:
        if row.analysis:
            continue
        result = analyze_text(
            text=row.text,
            rating=row.rating,
            segment=row.segment,
            similar_corpus=None,
            repeat_count=0,
        )
        persist_analysis(db, row, result, commit=False)
        analyzed += 1
        if analyzed % 100 == 0:
            db.commit()
            logger.info("Analyzed %s feedback records", analyzed)
    db.commit()
    return analyzed


def seed_if_needed(db: Session) -> dict[str, int]:
    _ensure_reference_data(db)
    if get_settings().app_env == "test":
        ensure_datasets()
        return {"training_rows": 0, "dummy_rows": 0, "created": 0}
    training_count, dummy_count = ensure_datasets()
    created = 0
    if db.query(Feedback).count() == 0:
        dummy_path = get_settings().data_path / "dummy_feedback.csv"
        logger.info("Importing dummy feedback from %s", dummy_path)
        created = _import_dummy(db, dummy_path)
        db.add(
            Dataset(
                name="dummy_feedback.csv",
                filename="dummy_feedback.csv",
                row_count=created,
                missing_values=0,
                duplicate_count=0,
                date_min="2025-12-01",
                date_max="2026-08-15",
            )
        )
        db.commit()
    logger.info(
        "Seed import complete training=%s dummy=%s created=%s",
        training_count,
        dummy_count,
        created,
    )
    return {
        "training_rows": training_count,
        "dummy_rows": dummy_count,
        "created": created,
    }
