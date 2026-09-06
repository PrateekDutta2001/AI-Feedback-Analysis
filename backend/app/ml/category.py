"""Category classification."""

from __future__ import annotations

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from backend.app.ml.model_registry import store
from backend.app.ml.preprocessing import clean_text

LABELS = (
    "Product",
    "Service",
    "Delivery",
    "Payment",
    "Pricing",
    "Customer Support",
    "Technical Issue",
    "Account",
    "UX/UI",
    "Performance",
    "Security",
    "Documentation",
    "Other",
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
                    max_features=12000,
                    sublinear_tf=True,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=500,
                    class_weight="balanced",
                    solver="lbfgs",
                ),
            ),
        ]
    )


def predict(text: str) -> dict[str, Any]:
    model = store.get("category")
    cleaned = clean_text(text)
    probabilities = model.predict_proba([cleaned])[0]
    mapping = {str(label): float(prob) for label, prob in zip(model.classes_, probabilities)}
    label = max(mapping, key=mapping.get)
    return {"category": label, "confidence": round(mapping[label], 4)}
