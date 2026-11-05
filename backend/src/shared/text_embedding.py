"""Deterministic, vendor-free text embeddings for local hybrid retrieval.

Canonical: .pi/architecture/modules/evidence-retrieval.md (dense branch)

This is a *feature-hashing* embedding, not a neural encoder: it maps German tokens and character
trigrams into a fixed-size signed vector. That is deliberate. The prototype must run without a
vendor account or network call, but the retrieval path still needs a real vector score to fuse and
to record honestly. A production deployment replaces this module behind ``EmbeddingPort`` and
updates the index manifest's model id; no retrieval code changes.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from typing import Final

MODEL_ID: Final[str] = "hashing-char3gram-v1"
DIMENSIONS: Final[int] = 384

_TOKEN_PATTERN = re.compile(r"[a-z0-9äöüß]+")


def embed_text(text: str) -> list[float]:
    """Return one L2-normalized feature-hashed vector for ``text``."""
    vector = [0.0] * DIMENSIONS
    for feature in _features(text):
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % DIMENSIONS
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[bucket] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Embed a batch; order is preserved."""
    return [embed_text(text) for text in texts]


def _features(text: str) -> list[str]:
    normalized = text.casefold()
    features: list[str] = []
    for token in _TOKEN_PATTERN.findall(normalized):
        features.append("w:" + token)
        if len(token) < 3:
            continue
        padded = f"#{token}#"
        features.extend("c:" + padded[index : index + 3] for index in range(len(padded) - 2))
    return features
