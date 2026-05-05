from __future__ import annotations

import math
import re
from collections import Counter


TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_+-]*")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def embed_text(text: str) -> dict[str, float]:
    counts = Counter(tokenize(text))
    norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
    return {token: value / norm for token, value in counts.items()}


def cosine_sparse(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(weight * right.get(token, 0.0) for token, weight in left.items())
