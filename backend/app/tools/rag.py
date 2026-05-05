from __future__ import annotations

from pathlib import Path


def retrieve_lab_manual(path: str | Path, query: str = "") -> dict[str, object]:
    manual_path = Path(path)
    if not manual_path.exists():
        return {"snippets": []}
    text = manual_path.read_text(errors="ignore")
    query_terms = {term.lower().strip(".,?") for term in query.split() if len(term) > 3}
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    scored = []
    for paragraph in paragraphs:
        score = sum(1 for term in query_terms if term in paragraph.lower())
        if "non-inverting" in paragraph.lower() or "saturates" in paragraph.lower():
            score += 2
        scored.append((score, paragraph))
    scored.sort(reverse=True, key=lambda item: item[0])
    snippets = [{"source": manual_path.name, "text": paragraph[:500]} for score, paragraph in scored[:3] if score > 0]
    if not snippets and paragraphs:
        snippets = [{"source": manual_path.name, "text": paragraphs[0][:500]}]
    return {"snippets": snippets}

