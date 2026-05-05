from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.request
from collections import Counter
from typing import Any


TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_+-]*")
BOW_DIMS = 384
_MODEL: Any | None = None


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def bow_embed_text(text: str, dims: int = BOW_DIMS) -> list[float]:
    counts = Counter(tokenize(text))
    vector = [0.0] * dims
    for token, count in counts.items():
        vector[hash(token) % dims] += float(count)
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _ollama_embed(text: str) -> list[float]:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    body = json.dumps({"model": model, "prompt": text}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/api/embeddings",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        data = json.loads(response.read())
    embedding = data.get("embedding")
    if not isinstance(embedding, list) or not embedding:
        raise RuntimeError("ollama embedding missing")
    return [float(value) for value in embedding]


def _sentence_transformer_embed(text: str) -> list[float]:
    if os.getenv("CIRCUITSAGE_EMBED_FALLBACK", "sentence-transformers") != "sentence-transformers":
        raise RuntimeError("sentence-transformers fallback disabled")
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        local_only = os.getenv("CIRCUITSAGE_ALLOW_EMBED_DOWNLOAD", "0") != "1"
        _MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", local_files_only=local_only)
    return [float(value) for value in _MODEL.encode(text, normalize_embeddings=True).tolist()]


def embed_with_metadata(text: str) -> tuple[list[float], str]:
    try:
        return _ollama_embed(text), "ollama"
    except (OSError, urllib.error.URLError, TimeoutError, RuntimeError, ValueError):
        pass
    try:
        return _sentence_transformer_embed(text), "sentence-transformers"
    except Exception:
        return bow_embed_text(text), "bow"


def embed_text(text: str) -> list[float]:
    return embed_with_metadata(text)[0]
