from __future__ import annotations

from pathlib import Path

from app.services import vectorstore


def test_vectorstore_ingest_and_query(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(vectorstore, "VECTORSTORE_PATH", tmp_path / "vectors.json")
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
