from __future__ import annotations

from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
import re

from ..config import get_settings
from .embedder import embed_with_metadata


CHROMA_PATH = get_settings().database_path.parent / "chroma"
COLLECTION_NAME = "circuitsage"
_CLIENT: Any | None = None
_COLLECTION: Any | None = None


def _collection():
    global _CLIENT, _COLLECTION
    if _CLIENT is None:
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        _CLIENT = chromadb.PersistentClient(path=str(CHROMA_PATH), settings=ChromaSettings(anonymized_telemetry=False))
    if _COLLECTION is None:
        _COLLECTION = _CLIENT.get_or_create_collection(COLLECTION_NAME)
    return _COLLECTION


def reset() -> None:
    global _COLLECTION
    collection = _collection()
    existing = collection.get()
    ids = existing.get("ids", [])
    if ids:
        collection.delete(ids=ids)
    _COLLECTION = collection


def ingest(doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
    embedding, embedder = embed_with_metadata(text)
    merged_metadata = {**(metadata or {}), "embedder": embedder}
    _collection().upsert(ids=[doc_id], embeddings=[embedding], documents=[text], metadatas=[merged_metadata])


def query(text: str, k: int = 5, filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    embedding, _ = embed_with_metadata(text)
    collection = _collection()
    n_results = min(max(k * 4, k), max(collection.count(), k))
    result = collection.query(query_embeddings=[embedding], n_results=n_results, where=filter or None)
    ids = result.get("ids", [[]])[0]
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    hits = []
    for doc_id, document, metadata, distance in zip(ids, docs, metas, distances):
        lexical = _lexical_score(text, document or "")
        source = metadata.get("source", doc_id)
        boost = 1.0 if str(source).startswith("faults/") and lexical > 0 else 0.0
        hits.append(
            {
                "doc_id": doc_id,
                "source": source,
                "text": document,
                "metadata": metadata,
                "score": round(float(1 - distance) + lexical + boost, 4),
            }
        )
    return sorted(hits, key=lambda hit: hit["score"], reverse=True)[:k]


def _lexical_score(query_text: str, document: str) -> float:
    terms = {term.lower() for term in re.findall(r"[a-zA-Z][a-zA-Z0-9_+-]*", query_text) if len(term) > 3}
    lowered = document.lower()
    return sum(1 for term in terms if term in lowered) / max(len(terms), 1)
