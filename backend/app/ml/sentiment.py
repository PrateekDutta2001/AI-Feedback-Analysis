"""Sentiment classification using TF-IDF and logistic regression."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from backend.app.ml.model_registry import store
from backend.app.ml.preprocessing import clean_text

LABELS = ("positive", "neutral", "negative")


def build_estimator() -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    preprocessor=clean_text,
                    ngram_range=(1, 2),
                    min_df=2,
                    max_features=12000,
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


def _proba_map(model: Pipeline, text: str) -> dict[str, float]:
    cleaned = clean_text(text)
    probabilities = model.predict_proba([cleaned])[0]
    mapping = {str(label).lower(): float(prob) for label, prob in zip(model.classes_, probabilities)}
    return {label: mapping.get(label, 0.0) for label in LABELS}


def predict(text: str) -> dict[str, Any]:
    model = store.get("sentiment")
    scores = _proba_map(model, text)
    label = max(scores, key=scores.get)
    return {
        "label": label,
        "score": round(scores[label], 4),
        "positive": round(scores["positive"], 4),
        "neutral": round(scores["neutral"], 4),
        "negative": round(scores["negative"], 4),
    }


def predict_batch(texts: list[str]) -> list[dict[str, Any]]:
    model = store.get("sentiment")
    cleaned = [clean_text(text) for text in texts]
    probabilities = model.predict_proba(cleaned)
    results = []
    for row in probabilities:
        mapping = {str(label).lower(): float(prob) for label, prob in zip(model.classes_, row)}
        scores = {label: mapping.get(label, 0.0) for label in LABELS}
        label = max(scores, key=scores.get)
        results.append(
            {
                "label": label,
                "score": round(scores[label], 4),
                "positive": round(scores["positive"], 4),
                "neutral": round(scores["neutral"], 4),
                "negative": round(scores["negative"], 4),
            }
        )
    return results


def sentiment_score(prediction: dict[str, Any]) -> float:
    """Map class probabilities to a -1 to 1 sentiment score."""
    return float(
        np.clip(
            prediction["positive"] - prediction["negative"],
            -1.0,
            1.0,
        )
    )
