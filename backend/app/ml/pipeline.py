"""End-to-end inference pipeline."""

from __future__ import annotations

from typing import Any

from backend.app.ml import category, emotion, intent, keywords, priority, sentiment
from backend.app.ml.insights import detect_aspects, explain_sentiment, recommend_action
from backend.app.ml.keywords import highlighted_phrases
from backend.app.ml.similarity import find_similar


def analyze_text(
    text: str,
    rating: int | None = None,
    segment: str | None = None,
    similar_corpus: list[dict[str, Any]] | None = None,
    repeat_count: int = 0,
    topic_names: list[str] | None = None,
) -> dict[str, Any]:
    """Run the full ML stack on a single feedback text."""
    sentiment_pred = sentiment.predict(text)
    emotion_pred = emotion.predict(text)
    category_pred = category.predict(text)
    intent_pred = intent.predict(text)
    keyword_list = keywords.extract_keywords(text)
    phrases = highlighted_phrases(text)
    priority_pred = priority.calculate_priority(
        text=text,
        sentiment=sentiment_pred,
        emotion=emotion_pred,
        intent=intent_pred["intent"],
        rating=rating,
        segment=segment,
        repeat_count=repeat_count,
    )
    severity_pred = priority.calculate_severity(
        text=text,
        sentiment=sentiment_pred,
        priority=priority_pred,
        rating=rating,
        category=category_pred["category"],
        repeat_count=repeat_count,
    )
    aspects = detect_aspects(text, sentiment_pred["label"], rating)
    analysis = {
        "sentiment": sentiment_pred,
        "emotion": emotion_pred,
        "category": category_pred["category"],
        "category_score": category_pred["confidence"],
        "intent": intent_pred["intent"],
        "intent_score": intent_pred["confidence"],
        "priority": priority_pred,
        "severity": severity_pred,
        "keywords": keyword_list,
        "key_phrases": phrases,
        "aspects": aspects,
        "topics": topic_names or [],
    }
    recommendation = recommend_action(analysis)
    analysis["recommendation"] = recommendation
    analysis["explanation"] = {
        "sentiment": explain_sentiment(sentiment_pred, phrases or [item["keyword"] for item in keyword_list[:3]]),
        "priority": priority_pred["reason"],
        "severity": severity_pred["reasons"],
    }
    if similar_corpus is not None:
        analysis["similar"] = find_similar(text, similar_corpus)
    else:
        analysis["similar"] = []
    return analysis


def analyze_batch(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        analyze_text(
            text=item["text"],
            rating=item.get("rating"),
            segment=item.get("segment"),
            repeat_count=item.get("repeat_count", 0),
        )
        for item in items
    ]
