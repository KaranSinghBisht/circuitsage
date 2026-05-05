from __future__ import annotations

from pathlib import Path

from app.services import vectorstore
from app.services.embedder import bow_embed_text
from app.tools import rag


def isolated_store(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(vectorstore, "CHROMA_PATH", tmp_path / "chroma")
    monkeypatch.setattr(vectorstore, "_CLIENT", None)
    monkeypatch.setattr(vectorstore, "_COLLECTION", None)
    monkeypatch.setattr(vectorstore, "embed_with_metadata", lambda text: (bow_embed_text(text), "bow"))


def test_retrieve_returns_right_doc_and_filters(tmp_path: Path, monkeypatch) -> None:
    isolated_store(tmp_path, monkeypatch)
    monkeypatch.setattr(rag, "vector_query", vectorstore.query)
    vectorstore.reset()
    vectorstore.ingest(
        "faults/floating_noninv_input.md#0",
        "floating non-inverting input op amp saturation ground",
        {"source": "faults/floating_noninv_input.md", "topology": "op_amp_inverting"},
    )
    vectorstore.ingest(
        "faults/wrong_capacitor_value.md#0",
        "wrong capacitor value rc low pass attenuation cutoff",
        {"source": "faults/wrong_capacitor_value.md", "topology": "rc_lowpass"},
    )

    op_amp = rag.retrieve("floating non-inverting input", topology="op_amp_inverting", k=1)
    rc = rag.retrieve("floating non-inverting input", topology="rc_lowpass", k=1)

    assert op_amp["snippets"][0]["source"] == "faults/floating_noninv_input.md"
    assert rc["snippets"][0]["source"] == "faults/wrong_capacitor_value.md"


def test_retrieve_places_session_artifacts_first(tmp_path: Path, monkeypatch) -> None:
    isolated_store(tmp_path, monkeypatch)
    monkeypatch.setattr(rag, "vector_query", vectorstore.query)
    vectorstore.reset()
    vectorstore.ingest("corpus#0", "op amp generic reference", {"source": "textbook/op_amp.md"})
    manual = tmp_path / "manual.md"
    manual.write_text("The floating non-inverting input is the local lab hint.")

    result = rag.retrieve(
        "floating non-inverting input",
        k=2,
        session_artifacts=[{"path": str(manual), "filename": "manual.md"}],
    )

    assert result["snippets"][0]["source"] == "manual.md"
    assert result["from_session"] == 1
