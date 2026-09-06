"""Emotion classification."""

from __future__ import annotations

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from backend.app.ml.model_registry import store
from backend.app.ml.preprocessing import clean_text

LABELS = (
    "joy",
    "satisfaction",
    "neutral",
    "frustration",
    "anger",
    "sadness",
    "confusion",
    "disappointment",
)


def build_estimator() -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    preprocessor=clean_text,
                    ngram_range=(1, 2),
                    min_df=1,
                    max_features=10000,
                    sublinear_tf=True,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=400,
                    class_weight="balanced",
                    solver="lbfgs",
                ),
            ),
        ]
    )


def predict(text: str) -> dict[str, Any]:
    model = store.get("emotion")
    cleaned = clean_text(text)
    probabilities = model.predict_proba([cleaned])[0]
    mapping = {str(label).lower(): float(prob) for label, prob in zip(model.classes_, probabilities)}
    label = max(mapping, key=mapping.get)
    return {"emotion": label, "confidence": round(mapping[label], 4)}


def predict_batch(texts: list[str]) -> list[dict[str, Any]]:
    return [predict(text) for text in texts]
