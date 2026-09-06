"""ML pipeline unit tests."""

from __future__ import annotations

from backend.app.ml import category, emotion, intent, keywords, priority, sentiment, similarity
from backend.app.ml.pipeline import analyze_text
from backend.app.ml.trainer import ensure_models


def setup_module(_module):
    ensure_models()


def test_sentiment_prediction():
    result = sentiment.predict("I love this product, it is excellent and wonderful.")
    assert result["label"] in {"positive", "neutral", "negative"}
    assert 0 <= result["score"] <= 1
    assert abs(result["positive"] + result["neutral"] + result["negative"] - 1) < 0.02


def test_negative_sentiment():
    result = sentiment.predict("Delivery was extremely late and customer support did not respond.")
    assert result["label"] == "negative"


def test_emotion_prediction():
    result = emotion.predict("I am so angry about the failed payment and unauthorized charge.")
    assert "emotion" in result
    assert result["confidence"] > 0


def test_category_prediction():
    result = category.predict("The courier lost my package and the delivery is late.")
    assert result["category"]


def test_intent_prediction():
    result = intent.predict("How do I export filtered analytics to CSV?")
    assert result["intent"]


def test_priority_calculation():
    result = priority.calculate_priority(
        text="critical outage and security breach",
        sentiment={"label": "negative", "negative": 0.9, "positive": 0.05, "neutral": 0.05},
        emotion={"emotion": "anger", "confidence": 0.8},
        intent="Complaint",
        rating=1,
        segment="Enterprise",
        repeat_count=4,
    )
    assert result["priority"] in {"high", "critical"}
    assert result["score"] >= 60
    assert result["reason"]


def test_keyword_extraction():
    result = keywords.extract_keywords("delivery delay and customer support response time")
    assert result
    assert result[0]["keyword"]


def test_similarity_detects_near_duplicates():
    score = similarity.pair_similarity(
        "Delivery was extremely late and customer support did not respond.",
        "Delivery was extremely late and the support team did not respond.",
    )
    assert score >= 0.5


def test_full_pipeline():
    result = analyze_text(
        "The mobile payment page failed and I was charged twice.",
        rating=1,
        segment="Enterprise",
    )
    assert result["category"]
    assert result["recommendation"]["action"]
    assert 1 <= result["severity"]["severity"] <= 5
