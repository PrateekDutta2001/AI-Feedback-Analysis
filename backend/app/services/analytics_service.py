"""Dashboard and analytics aggregations."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.ml.insights import ASPECT_LEXICON
from backend.app.ml.keywords import corpus_keywords
from backend.app.ml.topics import discover_topics
from backend.app.models.database_models import Feedback, FeedbackAnalysis
from backend.app.utils.helpers import as_utc, delta_percent, percent, safe_date

_DASHBOARD_CACHE: dict[str, Any] = {"expires": None, "payload": None}


def invalidate_cache() -> None:
    _DASHBOARD_CACHE["expires"] = None
    _DASHBOARD_CACHE["payload"] = None


def _base_query(db: Session, params: dict[str, Any] | None = None):
    query = db.query(Feedback).outerjoin(FeedbackAnalysis)
    params = params or {}
    if params.get("product"):
        query = query.filter(Feedback.product == params["product"])
    if params.get("department"):
        query = query.filter(Feedback.department == params["department"])
    if params.get("channel"):
        query = query.filter(Feedback.channel == params["channel"])
    if params.get("location"):
        query = query.filter(Feedback.location == params["location"])
    if params.get("segment"):
        query = query.filter(Feedback.segment == params["segment"])
    if params.get("date_from"):
        start = safe_date(params["date_from"])
        if start:
            query = query.filter(Feedback.date >= start)
    if params.get("date_to"):
        end = safe_date(params["date_to"])
        if end:
            query = query.filter(Feedback.date <= end)
    return query


def _rows(db: Session, params: dict[str, Any] | None = None) -> list[tuple[Feedback, FeedbackAnalysis | None]]:
    return _base_query(db, params).with_entities(Feedback, FeedbackAnalysis).all()


def _sentiment_counts(rows: list[tuple[Feedback, FeedbackAnalysis | None]]) -> dict[str, int]:
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for _, analysis in rows:
        if analysis and analysis.sentiment in counts:
            counts[analysis.sentiment] += 1
    return counts


def dashboard(db: Session, params: dict[str, Any] | None = None) -> dict[str, Any]:
    params = params or {}
    cache_key_empty = not any(params.get(key) for key in ("product", "department", "channel", "location", "segment", "date_from", "date_to"))
    now = datetime.now(timezone.utc)
    if cache_key_empty and _DASHBOARD_CACHE["payload"] and _DASHBOARD_CACHE["expires"] and _DASHBOARD_CACHE["expires"] > now:
        return _DASHBOARD_CACHE["payload"]

    rows = _rows(db, params)
    total = len(rows)
    sentiments = _sentiment_counts(rows)
    critical = sum(1 for _, analysis in rows if analysis and analysis.priority == "critical")
    resolved = sum(1 for feedback, _ in rows if feedback.status in {"resolved", "closed"})
    open_issues = sum(1 for feedback, _ in rows if feedback.status in {"open", "in_progress"})
    ratings = [feedback.rating for feedback, _ in rows]
    sentiment_scores = [
        (analysis.sentiment_positive - analysis.sentiment_negative)
        for _, analysis in rows
        if analysis
    ]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
    avg_sentiment = round(sum(sentiment_scores) / len(sentiment_scores), 3) if sentiment_scores else 0.0

    previous_params = dict(params)
    if params.get("date_from") and params.get("date_to"):
        start = safe_date(params["date_from"])
        end = safe_date(params["date_to"])
        if start and end:
            span = end - start
            previous_params["date_from"] = (start - span).isoformat()
            previous_params["date_to"] = start.isoformat()
            previous_rows = _rows(db, previous_params)
        else:
            previous_rows = []
    else:
        cutoff = now - timedelta(days=30)
        previous_rows = [
            item
            for item in rows
            if as_utc(item[0].date) and as_utc(item[0].date) < cutoff
        ]

    prev_total = len(previous_rows) or 1
    prev_sentiments = _sentiment_counts(previous_rows)
    prev_critical = sum(1 for _, analysis in previous_rows if analysis and analysis.priority == "critical")
    prev_ratings = [feedback.rating for feedback, _ in previous_rows]
    prev_avg_rating = (sum(prev_ratings) / len(prev_ratings)) if prev_ratings else avg_rating

    payload = {
        "kpis": {
            "total_feedback": total,
            "total_delta": delta_percent(total, prev_total if previous_rows else total),
            "positive_pct": percent(sentiments["positive"], total),
            "negative_pct": percent(sentiments["negative"], total),
            "neutral_pct": percent(sentiments["neutral"], total),
            "positive_delta": delta_percent(sentiments["positive"], prev_sentiments["positive"] or 1),
            "negative_delta": delta_percent(sentiments["negative"], prev_sentiments["negative"] or 1),
            "neutral_delta": delta_percent(sentiments["neutral"], prev_sentiments["neutral"] or 1),
            "critical": critical,
            "critical_delta": delta_percent(critical, prev_critical or 1),
            "avg_sentiment": avg_sentiment,
            "avg_rating": avg_rating,
            "rating_delta": round(avg_rating - prev_avg_rating, 2),
            "resolved": resolved,
            "open_issues": open_issues,
        },
        "charts": {
            "sentiment_distribution": sentiments,
            "sentiment_trend": _trend(rows, "sentiment"),
            "category": _count_map(rows, lambda analysis: analysis.category if analysis else "Unanalyzed"),
            "channel": _count_map_feedback(rows, lambda feedback: feedback.channel),
            "emotion": _count_map(rows, lambda analysis: analysis.emotion if analysis else "unknown"),
            "priority": _count_map(rows, lambda analysis: analysis.priority if analysis else "unknown"),
            "keywords": corpus_keywords([feedback.text for feedback, _ in rows], top_n=12),
            "departments": department_performance(db, params),
            "products": product_performance(db, params),
        },
    }
    if cache_key_empty:
        from backend.app.config import get_settings

        _DASHBOARD_CACHE["payload"] = payload
        _DASHBOARD_CACHE["expires"] = now + timedelta(seconds=get_settings().dashboard_cache_seconds)
    return payload


def _count_map(rows, getter) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter(getter(analysis) for _, analysis in rows)
    return [{"label": key, "value": value} for key, value in counter.most_common()]


def _count_map_feedback(rows, getter) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter(getter(feedback) for feedback, _ in rows)
    return [{"label": key, "value": value} for key, value in counter.most_common()]


def _trend(rows, field: str) -> list[dict[str, Any]]:
    buckets: dict[str, Counter[str]] = defaultdict(Counter)
    for feedback, analysis in rows:
        if not feedback.date:
            continue
        day = feedback.date.date().isoformat()
        if field == "sentiment":
            buckets[day][analysis.sentiment if analysis else "unknown"] += 1
        elif field == "rating":
            buckets[day]["rating_sum"] += feedback.rating
            buckets[day]["count"] += 1
        elif field == "category":
            buckets[day][analysis.category if analysis else "Unanalyzed"] += 1
        elif field == "emotion":
            buckets[day][analysis.emotion if analysis else "unknown"] += 1
        elif field == "priority":
            buckets[day][analysis.priority if analysis else "unknown"] += 1
        elif field == "volume":
            buckets[day]["count"] += 1
        elif field == "resolution":
            buckets[day]["total"] += 1
            if feedback.status in {"resolved", "closed"}:
                buckets[day]["resolved"] += 1
    series = []
    for day in sorted(buckets):
        item = {"date": day, **dict(buckets[day])}
        if field == "rating" and buckets[day]["count"]:
            item["avg_rating"] = round(buckets[day]["rating_sum"] / buckets[day]["count"], 2)
        if field == "resolution" and buckets[day]["total"]:
            item["rate"] = round((buckets[day]["resolved"] / buckets[day]["total"]) * 100, 2)
        series.append(item)
    return series[-60:]


def trends(db: Session, params: dict[str, Any]) -> dict[str, Any]:
    rows = _rows(db, params)
    return {
        "sentiment": _trend(rows, "sentiment"),
        "rating": _trend(rows, "rating"),
        "category": _trend(rows, "category"),
        "emotion": _trend(rows, "emotion"),
        "priority": _trend(rows, "priority"),
        "volume": _trend(rows, "volume"),
        "resolution": _trend(rows, "resolution"),
    }


def department_performance(db: Session, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows = _rows(db, params)
    grouped: dict[str, list[tuple[Feedback, FeedbackAnalysis | None]]] = defaultdict(list)
    for item in rows:
        grouped[item[0].department].append(item)
    results = []
    for name, items in grouped.items():
        sentiments = _sentiment_counts(items)
        total = len(items)
        ratings = [feedback.rating for feedback, _ in items]
        results.append(
            {
                "department": name,
                "feedback_count": total,
                "positive_pct": percent(sentiments["positive"], total),
                "negative_pct": percent(sentiments["negative"], total),
                "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
                "open_issues": sum(1 for feedback, _ in items if feedback.status in {"open", "in_progress"}),
                "critical_issues": sum(1 for _, analysis in items if analysis and analysis.priority == "critical"),
            }
        )
    results.sort(key=lambda item: (item["negative_pct"], item["critical_issues"]), reverse=True)
    for index, item in enumerate(results, start=1):
        item["rank"] = index
    return results


def product_performance(db: Session, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows = _rows(db, params)
    grouped: dict[str, list[tuple[Feedback, FeedbackAnalysis | None]]] = defaultdict(list)
    for item in rows:
        grouped[item[0].product].append(item)
    results = []
    for name, items in grouped.items():
        sentiments = _sentiment_counts(items)
        total = len(items)
        ratings = [feedback.rating for feedback, _ in items]
        negatives = [feedback.text for feedback, analysis in items if analysis and analysis.sentiment == "negative"]
        positives = [feedback.text for feedback, analysis in items if analysis and analysis.sentiment == "positive"]
        results.append(
            {
                "product": name,
                "feedback_volume": total,
                "sentiment": sentiments,
                "positive_pct": percent(sentiments["positive"], total),
                "negative_pct": percent(sentiments["negative"], total),
                "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
                "critical_issues": sum(1 for _, analysis in items if analysis and analysis.priority == "critical"),
                "top_complaints": corpus_keywords(negatives, top_n=5) if negatives else [],
                "top_positive_themes": corpus_keywords(positives, top_n=5) if positives else [],
            }
        )
    results.sort(key=lambda item: item["feedback_volume"], reverse=True)
    return results


def aspect_summary(db: Session, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows = _rows(db, params)
    summary = []
    for aspect, lexicon in ASPECT_LEXICON.items():
        matched = []
        for feedback, analysis in rows:
            lowered = feedback.text.lower()
            if any(word in lowered for word in lexicon):
                matched.append((feedback, analysis))
        total = len(matched)
        sentiments = _sentiment_counts(matched)
        ratings = [feedback.rating for feedback, _ in matched]
        summary.append(
            {
                "aspect": aspect,
                "mentions": total,
                "positive": percent(sentiments["positive"], total),
                "neutral": percent(sentiments["neutral"], total),
                "negative": percent(sentiments["negative"], total),
                "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
            }
        )
    summary.sort(key=lambda item: item["mentions"], reverse=True)
    return summary


def topics(db: Session, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows = _rows(db, params)
    records = [
        {
            "text": feedback.text,
            "sentiment": analysis.sentiment if analysis else "neutral",
            "date": feedback.date.isoformat() if feedback.date else None,
        }
        for feedback, analysis in rows
    ]
    return discover_topics(records)


def lookup_values(db: Session) -> dict[str, list[str]]:
    def distinct(column):
        return [value for (value,) in db.query(column).distinct().order_by(column.asc()).all() if value]

    return {
        "products": distinct(Feedback.product),
        "departments": distinct(Feedback.department),
        "channels": distinct(Feedback.channel),
        "locations": distinct(Feedback.location),
        "segments": distinct(Feedback.segment),
        "statuses": distinct(Feedback.status),
    }
