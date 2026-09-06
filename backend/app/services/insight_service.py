"""Dynamic insight generation from live database statistics."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.ml.insights import build_insight_statements
from backend.app.models.database_models import Feedback, FeedbackAnalysis
from backend.app.services.analytics_service import _rows, _sentiment_counts
from backend.app.utils.helpers import as_utc, percent


def _period_split(rows: list[tuple[Feedback, FeedbackAnalysis | None]], days: int = 30):
    dated = [(as_utc(item[0].date), item) for item in rows if as_utc(item[0].date)]
    if not dated:
        return rows, []
    dates = [item[0] for item in dated]
    latest = max(dates)
    earliest = min(dates)
    span_days = max((latest - earliest).days, days)
    window = max(days, span_days // 2)
    current_start = latest - timedelta(days=window)
    previous_start = current_start - timedelta(days=window)
    current = [item for _, item in dated if item[0].date and as_utc(item[0].date) >= current_start]
    previous = [
        item
        for _, item in dated
        if item[0].date and previous_start <= as_utc(item[0].date) < current_start
    ]
    return current, previous


def collect_stats(db: Session, params: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = _rows(db, params)
    current, previous = _period_split(rows)
    current_sent = _sentiment_counts(current)
    previous_sent = _sentiment_counts(previous)
    current_total = len(current) or 1
    previous_total = len(previous) or 1
    stats: dict[str, Any] = {
        "sentiment_delta": {
            "negative": round(
                (current_sent["negative"] / current_total) * 100
                - (previous_sent["negative"] / previous_total) * 100,
                1,
            ),
            "positive": round(
                (current_sent["positive"] / current_total) * 100
                - (previous_sent["positive"] / previous_total) * 100,
                1,
            ),
        }
    }

    negative_categories: Counter[str] = Counter()
    for _, analysis in current:
        if analysis and analysis.sentiment == "negative":
            negative_categories[analysis.category] += 1
    if negative_categories:
        category, count = negative_categories.most_common(1)[0]
        stats["top_negative_category"] = {
            "category": category,
            "count": count,
            "share": percent(count, current_sent["negative"] or 1),
        }

    channel_neg: dict[str, Counter[str]] = defaultdict(Counter)
    for feedback, analysis in current:
        if analysis and analysis.sentiment == "negative":
            channel_neg[feedback.channel][analysis.category] += 1
    best = None
    for channel, counter in channel_neg.items():
        if not counter:
            continue
        category, count = counter.most_common(1)[0]
        total_neg = sum(counter.values())
        share = percent(count, total_neg)
        if best is None or share > best["share"]:
            best = {"channel": channel, "category": category, "share": share, "count": count}
    if best:
        stats["channel_issue"] = best

    support_mentions = sum(
        1
        for feedback, analysis in current
        if analysis
        and analysis.sentiment == "negative"
        and any(term in feedback.text.lower() for term in ("response time", "did not respond", "no response", "support"))
    )
    if support_mentions:
        stats["support_mentions"] = {"count": support_mentions}

    def avg_rating(items):
        values = [feedback.rating for feedback, _ in items]
        return sum(values) / len(values) if values else 0.0

    stats["rating_delta"] = round(avg_rating(current) - avg_rating(previous), 2)

    def payment_positive_share(items):
        relevant = [
            analysis
            for _, analysis in items
            if analysis and analysis.category == "Payment"
        ]
        if not relevant:
            return 0.0
        positive = sum(1 for analysis in relevant if analysis.sentiment == "positive")
        return percent(positive, len(relevant))

    current_payment = payment_positive_share(current)
    previous_payment = payment_positive_share(previous)
    if current_payment or previous_payment:
        change = round(current_payment - previous_payment, 1)
        stats["payment_improvement"] = {
            "change": abs(change),
            "direction": "improved" if change >= 0 else "declined",
        }

    location_neg: dict[str, Counter[str]] = defaultdict(Counter)
    for feedback, analysis in current:
        if analysis and analysis.sentiment == "negative":
            location_neg[analysis.category][feedback.location] += 1
    if location_neg:
        category, counter = max(location_neg.items(), key=lambda item: sum(item[1].values()))
        top_locations = [name for name, _ in counter.most_common(2)]
        if top_locations:
            stats["location_issue"] = {"category": category, "locations": top_locations}

    emerging_terms = ("authentication", "login", "timeout", "refund", "delivery")
    dates = [as_utc(item[0].date) for item in rows if as_utc(item[0].date)]
    now = max(dates) if dates else datetime.now(timezone.utc)
    earliest = min(dates) if dates else now
    window = max(7, (now - earliest).days // 8)
    recent_start = now - timedelta(days=window)
    prev_start = now - timedelta(days=window * 2)
    best_term = None
    for term in emerging_terms:
        recent = sum(
            1
            for feedback, _ in rows
            if as_utc(feedback.date) and as_utc(feedback.date) >= recent_start and term in feedback.text.lower()
        )
        earlier = sum(
            1
            for feedback, _ in rows
            if as_utc(feedback.date) and prev_start <= as_utc(feedback.date) < recent_start and term in feedback.text.lower()
        )
        if recent >= 5 and recent > earlier * 1.4:
            candidate = {"term": term, "recent": recent, "previous": earlier, "window": window}
            if best_term is None or recent - earlier > best_term["recent"] - best_term["previous"]:
                best_term = candidate
    if best_term:
        stats["emerging_term"] = best_term

    open_count = sum(1 for feedback, _ in current if feedback.status in {"open", "in_progress"})
    resolved = sum(1 for feedback, _ in current if feedback.status in {"resolved", "closed"})
    stats["resolution"] = {
        "open": open_count,
        "rate": percent(resolved, len(current) or 1),
    }
    return stats


def generate_insights(db: Session, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return build_insight_statements(collect_stats(db, params))
