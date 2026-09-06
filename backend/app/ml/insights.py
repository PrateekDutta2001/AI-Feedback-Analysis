"""Deterministic insight and recommendation generation from statistics."""

from __future__ import annotations

from typing import Any

from backend.app.utils.helpers import delta_percent


ASPECT_LEXICON = {
    "Delivery": ["delivery", "courier", "shipping", "package", "late", "delay"],
    "Price": ["price", "pricing", "expensive", "cost", "cheap", "fee"],
    "Support": ["support", "agent", "ticket", "response", "helpdesk", "representative"],
    "Product Quality": ["quality", "defect", "broken", "damaged", "build"],
    "Performance": ["slow", "lag", "performance", "timeout", "loading"],
    "Payment": ["payment", "checkout", "card", "billing", "invoice", "refund"],
    "UX": ["ui", "ux", "interface", "design", "navigation", "confusing", "layout"],
}


def detect_aspects(text: str, sentiment_label: str, rating: int | None) -> list[dict[str, Any]]:
    lowered = text.lower()
    aspects = []
    for name, keywords in ASPECT_LEXICON.items():
        hits = [word for word in keywords if word in lowered]
        if hits:
            aspects.append(
                {
                    "aspect": name,
                    "mentions": hits,
                    "sentiment": sentiment_label,
                    "rating": rating,
                }
            )
    return aspects


def recommend_action(analysis: dict[str, Any]) -> dict[str, str]:
    category = analysis.get("category", "Other")
    priority = analysis.get("priority", {}).get("priority", "low")
    severity = analysis.get("severity", {}).get("severity", 1)
    intent = analysis.get("intent", "Information")
    sentiment = analysis.get("sentiment", {}).get("label", "neutral")

    if category == "Security" or severity >= 5:
        action = "Escalate immediately to Security and Engineering on-call."
    elif category == "Customer Support" and sentiment == "negative":
        action = "Escalate to Customer Support Operations."
    elif category == "Delivery" and sentiment == "negative":
        action = "Investigate delivery SLA and partner performance."
    elif category == "Payment":
        action = "Review payment and billing operations for failed transactions."
    elif category == "Technical Issue" or intent == "Bug Report":
        action = "Create or update an Engineering incident ticket."
    elif intent == "Feature Request":
        action = "Route to Product for backlog evaluation."
    elif intent == "Suggestion":
        action = "Share with the owning department for process improvement."
    elif sentiment == "positive":
        action = "Share as a customer success highlight with the owning team."
    else:
        action = "Monitor the issue and follow up with the customer."

    if priority in {"high", "critical"}:
        action = action.replace("Monitor", "Prioritize and resolve")

    reason_parts = [
        f"The feedback contains {sentiment} sentiment",
        f"category {category}",
        f"intent {intent}",
        f"and a severity score of {severity}/5",
    ]
    if analysis.get("priority", {}).get("reason"):
        reason_parts.append("Priority signals: " + ", ".join(analysis["priority"]["reason"][:3]))
    return {"action": action, "reason": ". ".join(reason_parts) + "."}


def build_insight_statements(stats: dict[str, Any]) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []

    sentiment_delta = stats.get("sentiment_delta") or {}
    if sentiment_delta.get("negative") is not None:
        change = sentiment_delta["negative"]
        direction = "increased" if change > 0 else "decreased"
        insights.append(
            {
                "type": "negative_trend" if change > 0 else "positive_trend",
                "title": "Negative sentiment movement",
                "message": f"Negative feedback {direction} by {abs(change):.1f}% versus the previous period.",
                "severity": "high" if change > 10 else "medium" if change > 0 else "low",
            }
        )

    if stats.get("top_negative_category"):
        item = stats["top_negative_category"]
        insights.append(
            {
                "type": "negative_trend",
                "title": "Dominant negative topic",
                "message": (
                    f"{item['category']} is the most common negative topic "
                    f"with {item['count']} records ({item['share']:.1f}% of negative feedback)."
                ),
                "severity": "high" if item["share"] >= 25 else "medium",
            }
        )

    if stats.get("channel_issue"):
        item = stats["channel_issue"]
        insights.append(
            {
                "type": "emerging_issue",
                "title": "Channel-specific complaints",
                "message": (
                    f"{item['channel']} users report higher {item['category'].lower()}-related complaints "
                    f"({item['share']:.1f}% of that channel's negative feedback)."
                ),
                "severity": "medium",
            }
        )

    if stats.get("support_mentions"):
        item = stats["support_mentions"]
        insights.append(
            {
                "type": "business_recommendation",
                "title": "Support response time",
                "message": (
                    f"Customer support response time is frequently mentioned in negative reviews "
                    f"({item['count']} mentions)."
                ),
                "severity": "medium",
            }
        )

    if stats.get("rating_delta") is not None:
        change = stats["rating_delta"]
        direction = "improved" if change > 0 else "dropped"
        insights.append(
            {
                "type": "positive_trend" if change > 0 else "negative_trend",
                "title": "Average rating change",
                "message": f"Average rating {direction} by {abs(change):.2f} points versus the previous period.",
                "severity": "low" if change >= 0 else "high",
            }
        )

    if stats.get("payment_improvement"):
        item = stats["payment_improvement"]
        insights.append(
            {
                "type": "positive_trend",
                "title": "Payment satisfaction",
                "message": (
                    f"Payment satisfaction {item['direction']} by {item['change']:.1f}% over the previous period."
                ),
                "severity": "low",
            }
        )

    if stats.get("location_issue"):
        item = stats["location_issue"]
        insights.append(
            {
                "type": "business_recommendation",
                "title": "Location SLA review",
                "message": (
                    f"Review {item['category'].lower()} partner SLA performance for "
                    f"{', '.join(item['locations'])}."
                ),
                "severity": "high",
            }
        )

    if stats.get("emerging_term"):
        item = stats["emerging_term"]
        insights.append(
            {
                "type": "emerging_issue",
                "title": "Emerging issue",
                "message": (
                    f"{item['term'].title()} mentions have increased significantly "
                    f"over the last {item['window']} days ({item['recent']} vs {item['previous']} earlier)."
                ),
                "severity": "high",
            }
        )

    if stats.get("resolution"):
        item = stats["resolution"]
        insights.append(
            {
                "type": "business_recommendation",
                "title": "Resolution rate",
                "message": (
                    f"Resolution rate is {item['rate']:.1f}% with {item['open']} open issues remaining."
                ),
                "severity": "medium" if item["rate"] < 60 else "low",
            }
        )

    return insights


def explain_sentiment(prediction: dict[str, Any], phrases: list[str]) -> str:
    label = prediction["label"]
    confidence = prediction["score"]
    phrase_text = ", ".join(f'"{item}"' for item in phrases[:3]) if phrases else "overall wording and tone"
    return (
        f"Classified as {label} with {confidence:.0%} confidence based on {phrase_text} "
        f"and class probabilities "
        f"(positive {prediction['positive']:.0%}, neutral {prediction['neutral']:.0%}, "
        f"negative {prediction['negative']:.0%})."
    )


def period_change(current: float, previous: float) -> dict[str, Any]:
    return {
        "current": current,
        "previous": previous,
        "change": delta_percent(current, previous),
        "direction": "improved" if current > previous else "declined" if current < previous else "unchanged",
    }
