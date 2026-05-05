from __future__ import annotations

from pathlib import Path

from app.services import vectorstore
from app.services.embedder import bow_embed_text


def isolated_store(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(vectorstore, "CHROMA_PATH", tmp_path / "chroma")
    monkeypatch.setattr(vectorstore, "_CLIENT", None)
    monkeypatch.setattr(vectorstore, "_COLLECTION", None)
    monkeypatch.setattr(vectorstore, "embed_with_metadata", lambda text: (bow_embed_text(text), "bow"))


def test_vectorstore_ingest_and_query(tmp_path: Path, monkeypatch) -> None:
    isolated_store(tmp_path, monkeypatch)
    vectorstore.reset()
    vectorstore.ingest(
        "faults/floating_noninv_input.md#0",
        "floating non-inverting input op amp saturation V_noninv ground",
        {"source": "faults/floating_noninv_input.md", "topology": "op_amp_inverting"},
    )
    vectorstore.ingest(
        "textbook/rc_filters.md#0",
        "rc low pass cutoff capacitor attenuation",
        {"source": "textbook/rc_filters.md", "topology": "rc_lowpass"},
    )

    hits = vectorstore.query("non-inverting input floating", k=1)
    assert hits[0]["source"] == "faults/floating_noninv_input.md"

    filtered = vectorstore.query("input floating", k=3, filter={"topology": "rc_lowpass"})
    assert filtered[0]["source"] == "textbook/rc_filters.md"


def test_dense_embedding_dimension_is_large_enough() -> None:
    assert len(bow_embed_text("non-inverting input floating")) >= 256
