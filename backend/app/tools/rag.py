from __future__ import annotations

from pathlib import Path
from typing import Any

from ..services.vectorstore import query as vector_query


def _paragraphs(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [paragraph.strip() for paragraph in path.read_text(errors="ignore").split("\n\n") if paragraph.strip()]


def _term_score(text: str, query: str) -> float:
    terms = {term.lower().strip(".,?:;()") for term in query.split() if len(term) > 3}
    lowered = text.lower()
    return sum(1 for term in terms if term in lowered) / max(len(terms), 1)


def retrieve(
    query: str,
    *,
    topology: str | None = None,
    k: int = 4,
    session_artifacts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    session_hits: list[dict[str, Any]] = []
    for artifact in session_artifacts or []:
        path = Path(artifact["path"])
        for index, paragraph in enumerate(_paragraphs(path)):
            score = _term_score(paragraph, query)
            if score > 0:
                session_hits.append(
                    {
                        "source": artifact.get("filename", path.name),
                        "text": paragraph[:700],
                        "score": round(1.0 + score, 4),
                        "metadata": {"source": "session", "paragraph": index},
                    }
                )

    corpus_filter = {"topology": topology} if topology else None
    corpus_hits = vector_query(query, k=k, filter=corpus_filter)
    if topology and len(corpus_hits) < k:
        seen = {hit["doc_id"] for hit in corpus_hits}
        corpus_hits.extend(hit for hit in vector_query(query, k=k) if hit["doc_id"] not in seen)
    for hit in corpus_hits:
        if str(hit.get("source", "")).startswith("faults/"):
            hit["score"] = round(float(hit.get("score", 0.0)) + 1.0, 4)

    snippets = sorted([*session_hits, *corpus_hits], key=lambda hit: hit["score"], reverse=True)[:k]
    return {
        "snippets": snippets,
        "from_corpus": len([hit for hit in snippets if hit.get("metadata", {}).get("source") != "session"]),
        "from_session": len([hit for hit in snippets if hit.get("metadata", {}).get("source") == "session"]),
    }


def retrieve_lab_manual(path: str | Path, query: str = "") -> dict[str, Any]:
    return retrieve(query, session_artifacts=[{"path": str(path), "filename": Path(path).name}], k=3)
