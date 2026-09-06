"""Topic discovery using TF-IDF and KMeans."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from backend.app.ml.preprocessing import clean_text


def discover_topics(
    records: list[dict[str, Any]],
    n_topics: int = 8,
) -> list[dict[str, Any]]:
    texts = [clean_text(record["text"]) for record in records]
    usable = [(idx, text) for idx, text in enumerate(texts) if text]
    if len(usable) < 6:
        return []

    indexes, cleaned = zip(*usable)
    cluster_count = max(2, min(n_topics, len(cleaned) // 8 or 2, 10))
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        max_features=5000,
        stop_words="english",
    )
    matrix = vectorizer.fit_transform(cleaned)
    model = KMeans(n_clusters=cluster_count, n_init=8, random_state=42)
    labels = model.fit_predict(matrix)
    terms = np.array(vectorizer.get_feature_names_out())

    grouped: dict[int, list[int]] = defaultdict(list)
    for local_idx, label in enumerate(labels):
        grouped[int(label)].append(int(indexes[local_idx]))

    topics: list[dict[str, Any]] = []
    order = 1
    for cluster_id, source_indexes in grouped.items():
        centroid = model.cluster_centers_[cluster_id]
        top_term_idx = centroid.argsort()[::-1][:6]
        keywords = [str(terms[i]) for i in top_term_idx]
        name = _topic_name(keywords)
        subset = [records[i] for i in source_indexes]
        sentiments = Counter(item.get("sentiment", "neutral") for item in subset)
        total = len(subset)
        negative_pct = round((sentiments.get("negative", 0) / total) * 100, 1) if total else 0.0
        topics.append(
            {
                "id": order,
                "name": name,
                "feedback_count": total,
                "sentiment": {
                    "positive": sentiments.get("positive", 0),
                    "neutral": sentiments.get("neutral", 0),
                    "negative": sentiments.get("negative", 0),
                    "negative_pct": negative_pct,
                },
                "top_keywords": keywords,
                "trend": _trend(subset),
            }
        )
        order += 1

    topics.sort(key=lambda item: item["feedback_count"], reverse=True)
    return topics


def assign_topics_for_text(text: str, topics: list[dict[str, Any]]) -> list[str]:
    cleaned = clean_text(text)
    assigned = []
    for topic in topics:
        if any(keyword in cleaned for keyword in topic.get("top_keywords", [])[:4]):
            assigned.append(topic["name"])
    return assigned[:3]


def _topic_name(keywords: list[str]) -> str:
    if not keywords:
        return "General feedback"
    primary = keywords[0].title()
    mapping = {
        "delivery": "Delivery delays",
        "support": "Customer support experience",
        "payment": "Payment friction",
        "login": "Authentication issues",
        "price": "Pricing concerns",
        "app": "Mobile app experience",
        "slow": "Performance issues",
        "refund": "Refund and billing",
        "security": "Security and trust",
        "ui": "Interface usability",
    }
    for key, label in mapping.items():
        if any(key in keyword for keyword in keywords):
            return label
    return primary


def _trend(subset: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for item in subset:
        date_value = str(item.get("date") or "")[:10]
        if date_value:
            counts[date_value] += 1
    return [{"date": day, "count": counts[day]} for day in sorted(counts)][-14:]
