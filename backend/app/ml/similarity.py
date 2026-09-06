"""Near-duplicate detection using TF-IDF cosine similarity."""

from __future__ import annotations

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.app.config import get_settings
from backend.app.ml.preprocessing import clean_text


def find_similar(
    text: str,
    corpus: list[dict[str, Any]],
    threshold: float | None = None,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    if not corpus:
        return []
    settings = get_settings()
    cutoff = settings.similarity_threshold if threshold is None else threshold
    documents = [clean_text(text)] + [clean_text(item["text"]) for item in corpus]
    if all(not doc for doc in documents):
        return []
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words="english")
    try:
        matrix = vectorizer.fit_transform(documents)
    except ValueError:
        return []
    scores = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    matches: list[dict[str, Any]] = []
    for item, score in zip(corpus, scores):
        value = float(score)
        if value >= cutoff:
            matches.append(
                {
                    "feedback_id": item.get("feedback_id"),
                    "id": item.get("id"),
                    "text": item.get("text"),
                    "similarity": round(value, 4),
                }
            )
    matches.sort(key=lambda row: row["similarity"], reverse=True)
    return matches[:top_n]


def pair_similarity(left: str, right: str) -> float:
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    try:
        matrix = vectorizer.fit_transform([clean_text(left), clean_text(right)])
    except ValueError:
        return 0.0
    return float(cosine_similarity(matrix[0:1], matrix[1:]).flatten()[0])
