"""Keyword and key-phrase extraction using TF-IDF and n-grams."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer

from backend.app.ml.preprocessing import clean_text

_STOP = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "was",
    "were",
    "are",
    "have",
    "has",
    "had",
    "but",
    "not",
    "you",
    "your",
    "our",
    "from",
    "they",
    "them",
    "been",
    "very",
    "just",
    "also",
    "into",
    "than",
    "then",
    "when",
    "what",
    "which",
    "there",
    "their",
    "about",
    "would",
    "could",
    "should",
    "will",
    "can",
    "did",
    "does",
    "its",
    "it's",
}


def extract_keywords(text: str, top_n: int = 8) -> list[dict[str, Any]]:
    cleaned = clean_text(text)
    if not cleaned:
        return []

    tokens = [token for token in cleaned.split() if token not in _STOP and len(token) > 2]
    unigrams = Counter(tokens)
    bigrams = Counter(f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1))
    trigrams = Counter(f"{tokens[i]} {tokens[i + 1]} {tokens[i + 2]}" for i in range(len(tokens) - 2))

    scored: dict[str, float] = {}
    for term, count in unigrams.items():
        scored[term] = count * 0.6
    for term, count in bigrams.items():
        scored[term] = count * 1.15
    for term, count in trigrams.items():
        scored[term] = count * 1.35

    if not scored:
        return []

    peak = max(scored.values()) or 1.0
    ranked = sorted(scored.items(), key=lambda item: item[1], reverse=True)[:top_n]
    return [{"keyword": term, "score": round(value / peak, 4)} for term, value in ranked]


def corpus_keywords(texts: list[str], top_n: int = 15) -> list[dict[str, Any]]:
    cleaned = [clean_text(text) for text in texts if clean_text(text)]
    if len(cleaned) < 2:
        merged = " ".join(cleaned)
        return extract_keywords(merged, top_n=top_n)
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        max_features=4000,
        stop_words="english",
    )
    matrix = vectorizer.fit_transform(cleaned)
    weights = matrix.mean(axis=0).A1
    terms = vectorizer.get_feature_names_out()
    pairs = sorted(zip(terms, weights), key=lambda item: item[1], reverse=True)[:top_n]
    peak = pairs[0][1] if pairs else 1.0
    return [{"keyword": term, "score": round(float(score / peak), 4)} for term, score in pairs]


def highlighted_phrases(text: str) -> list[str]:
    matches = re.findall(
        r"(extremely \w+|did not \w+|never \w+|too \w+|very \w+|cannot \w+|unable to \w+)",
        text.lower(),
    )
    return list(dict.fromkeys(matches))[:6]
