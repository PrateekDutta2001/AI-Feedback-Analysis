"""Train, evaluate, and persist InsightAI models."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

from backend.app.config import get_settings
from backend.app.ml import category, emotion, intent, sentiment
from backend.app.ml.model_registry import MODEL_NAMES, store
from backend.app.utils.logger import get_logger

logger = get_logger("insightai.ml.trainer")

MODEL_BUILDERS = {
    "sentiment": (sentiment.build_estimator, "sentiment"),
    "emotion": (emotion.build_estimator, "emotion"),
    "category": (category.build_estimator, "category"),
    "intent": (intent.build_estimator, "intent"),
}


def load_training_frame() -> pd.DataFrame:
    settings = get_settings()
    path = settings.data_path / "training_data.csv"
    if not path.exists():
        raise FileNotFoundError(f"Training dataset not found: {path}")
    frame = pd.read_csv(path)
    required = {"text", "sentiment", "emotion", "category", "intent"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Training data missing columns: {sorted(missing)}")
    return frame.dropna(subset=["text"]).copy()


def _metrics(y_true, y_pred, labels: list[str] | None = None) -> dict[str, Any]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, average="weighted", zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average="weighted", zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist() if labels else confusion_matrix(y_true, y_pred).tolist(),
        "labels": labels or sorted(set(y_true) | set(y_pred)),
        "report": classification_report(y_true, y_pred, zero_division=0, output_dict=True),
    }


def train_one(name: str, frame: pd.DataFrame, version: str) -> dict[str, Any]:
    builder, column = MODEL_BUILDERS[name]
    data = frame[["text", column]].dropna()
    labels = data[column].astype(str)
    stratify = labels if labels.value_counts().min() >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(
        data["text"].astype(str),
        labels,
        test_size=0.2,
        random_state=42,
        stratify=stratify,
    )
    model = builder()
    model.fit(x_train, y_train)
    predicted = model.predict(x_test)
    labels = sorted(set(y_train) | set(y_test))
    metrics = _metrics(y_test, predicted, labels=labels)
    metadata = {
        "name": name,
        "version": version,
        "algorithm": "TF-IDF + Logistic Regression",
        "training_date": datetime.now(timezone.utc).isoformat(),
        "dataset_size": int(len(data)),
        "status": "active",
        **metrics,
    }
    store.save(name, model, metadata)
    logger.info("Trained %s accuracy=%.3f f1=%.3f", name, metrics["accuracy"], metrics["f1"])
    return metadata


def train_all(version: str | None = None) -> list[dict[str, Any]]:
    frame = load_training_frame()
    stamp = version or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    results = [train_one(name, frame, stamp) for name in MODEL_NAMES]
    summary_path = get_settings().model_path / "training_summary.json"
    summary_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    return results


def ensure_models() -> list[dict[str, Any]] | None:
    if store.all_exist():
        store.load_all()
        logger.info("Existing models loaded; training skipped.")
        return None
    logger.info("Model files missing; training from dataset.")
    return train_all(version="1.0.0")
