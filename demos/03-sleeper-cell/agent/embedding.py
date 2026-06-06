"""Deterministic local embeddings for Demo 03 Chroma retrieval."""

from __future__ import annotations

import hashlib
import math
import re


EMBEDDING_DIMENSIONS = 128
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Return normalized tokens used by the local embedding function."""
    return _TOKEN_PATTERN.findall(text.lower())


def embed_text(text: str) -> list[float]:
    """Create a stable hashed bag-of-words embedding for local demo retrieval."""
    vector = [0.0] * EMBEDDING_DIMENSIONS

    for token in tokenize(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign

    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return vector

    return [value / magnitude for value in vector]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Create embeddings for a list of texts."""
    return [embed_text(text) for text in texts]
