"""Transparent priority and severity scoring."""

from __future__ import annotations

from typing import Any

from backend.app.utils.helpers import clamp

SEVERITY_KEYWORDS = {
    "critical": 28,
    "urgent": 24,
    "outage": 26,
    "down": 22,
    "breach": 30,
    "security": 22,
    "fraud": 26,
    "refund": 14,
    "lawsuit": 30,
    "never": 10,
    "worst": 16,
    "broken": 14,
    "crash": 18,
    "failed": 14,
    "cannot": 12,
    "unable": 12,
    "late": 10,
    "delay": 10,
    "lost": 16,
    "charge": 10,
    "unauthorized": 24,
}

NEGATIVE_EMOTIONS = {"anger", "frustration", "disappointment", "sadness"}
HIGH_IMPACT_SEGMENTS = {"Enterprise", "Partner"}
COMPLAINT_INTENTS = {"Complaint", "Bug Report"}


def _keyword_weight(text: str) -> tuple[float, list[str]]:
    lowered = text.lower()
    score = 0.0
    hits: list[str] = []
    for word, weight in SEVERITY_KEYWORDS.items():
        if word in lowered:
            score += weight
            hits.append(word)
    return min(score, 40.0), hits


def calculate_priority(
    text: str,
    sentiment: dict[str, Any],
    emotion: dict[str, Any],
    intent: str,
    rating: int | None,
    segment: str | None = None,
    repeat_count: int = 0,
) -> dict[str, Any]:
    reasons: list[str] = []
    score = 10.0

    sentiment_weight = sentiment.get("negative", 0.0) * 35
    if sentiment.get("label") == "negative":
        reasons.append("Strong negative sentiment")
        score += sentiment_weight
    elif sentiment.get("label") == "positive":
        score -= 15

    if rating is not None:
        rating_weight = {1: 25, 2: 18, 3: 6, 4: 0, 5: -8}.get(rating, 0)
        score += rating_weight
        if rating <= 2:
            reasons.append("Low rating")

    emotion_label = emotion.get("emotion", "neutral")
    if emotion_label in NEGATIVE_EMOTIONS:
        score += 12 + emotion.get("confidence", 0.0) * 8
        reasons.append(f"Emotion indicates {emotion_label}")

    if intent in COMPLAINT_INTENTS:
        score += 12
        reasons.append("Complaint type feedback")
    elif intent == "Bug Report":
        score += 14
        reasons.append("Reported as a bug")

    keyword_score, hits = _keyword_weight(text)
    score += keyword_score
    if hits:
        reasons.append(f"Severity keywords: {', '.join(hits[:4])}")

    frequency_weight = min(repeat_count, 8) * 4
    score += frequency_weight
    if repeat_count >= 3:
        reasons.append("Repeated issue")

    if segment in HIGH_IMPACT_SEGMENTS:
        score += 10
        reasons.append(f"{segment} customer impact")

    score = clamp(score, 0, 100)
    if score >= 80:
        priority = "critical"
    elif score >= 60:
        priority = "high"
    elif score >= 35:
        priority = "medium"
    else:
        priority = "low"

    if not reasons:
        reasons.append("No elevated risk signals detected")

    return {
        "priority": priority,
        "score": round(score, 1),
        "reason": reasons,
    }


def calculate_severity(
    text: str,
    sentiment: dict[str, Any],
    priority: dict[str, Any],
    rating: int | None,
    category: str,
    repeat_count: int = 0,
) -> dict[str, Any]:
    lowered = text.lower()
    operational = any(word in lowered for word in ("outage", "down", "crash", "failed", "broken", "delay"))
    financial = any(word in lowered for word in ("refund", "charge", "billing", "payment", "price", "invoice"))
    security = any(word in lowered for word in ("security", "breach", "fraud", "unauthorized", "password", "hack"))
    customer_impact = sentiment.get("negative", 0.0) > 0.55 or (rating is not None and rating <= 2)

    score = 1
    reasons: list[str] = []
    if customer_impact:
        score += 1
        reasons.append("High customer impact")
    if operational:
        score += 1
        reasons.append("Operational impact detected")
    if financial:
        score += 1
        reasons.append("Financial impact detected")
    if security:
        score += 1
        reasons.append("Security impact detected")
    if repeat_count >= 4:
        score += 1
        reasons.append("High frequency of similar issues")
    if category in {"Security", "Payment", "Technical Issue"} and sentiment.get("label") == "negative":
        score += 1
        reasons.append(f"{category} issues increase severity")
    if priority["priority"] == "critical":
        score += 1
        reasons.append("Priority engine marked this as critical")

    score = int(clamp(score, 1, 5))
    labels = {1: "Minor", 2: "Low", 3: "Moderate", 4: "High", 5: "Critical"}
    return {
        "severity": score,
        "label": labels[score],
        "reasons": reasons or ["Limited operational or customer impact"],
    }
