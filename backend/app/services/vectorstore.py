from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import get_settings
from .embedder import cosine_sparse, embed_text


VECTORSTORE_PATH = get_settings().database_path.parent / "vectorstore.json"


def _read() -> list[dict[str, Any]]:
    if not VECTORSTORE_PATH.exists():
        return []
    return json.loads(VECTORSTORE_PATH.read_text())


def _write(records: list[dict[str, Any]]) -> None:
    VECTORSTORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    VECTORSTORE_PATH.write_text(json.dumps(records, indent=2))


def reset() -> None:
    _write([])


def ingest(doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
    records = [record for record in _read() if record["doc_id"] != doc_id]
    records.append(
        {
            "doc_id": doc_id,
            "text": text,
            "metadata": metadata or {},
            "embedding": embed_text(text),
        }
    )
    _write(records)


def query(text: str, k: int = 5, filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    needle = embed_text(text)
    hits: list[dict[str, Any]] = []
    for record in _read():
        metadata = record.get("metadata", {})
        if filter and any(metadata.get(key) != value for key, value in filter.items()):
            continue
        score = cosine_sparse(needle, record.get("embedding", {}))
        hits.append(
            {
                "doc_id": record["doc_id"],
                "source": metadata.get("source", record["doc_id"]),
                "text": record["text"],
                "metadata": metadata,
                "score": round(score, 4),
            }
        )
    return sorted(hits, key=lambda hit: hit["score"], reverse=True)[:k]
