"""Text cleaning and normalization for the ML pipeline."""

from __future__ import annotations

import re

_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_NON_ALPHA_RE = re.compile(r"[^a-z0-9\s']")
_SPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """Lowercase, strip URLs/emails, and normalize whitespace."""
    if not text:
        return ""
    value = str(text).lower()
    value = _URL_RE.sub(" ", value)
    value = _EMAIL_RE.sub(" ", value)
    value = value.replace("&", " and ")
    value = _NON_ALPHA_RE.sub(" ", value)
    value = _SPACE_RE.sub(" ", value).strip()
    return value


def tokenize(text: str) -> list[str]:
    return [token for token in clean_text(text).split(" ") if token]


def batch_clean(texts: list[str]) -> list[str]:
    return [clean_text(text) for text in texts]
