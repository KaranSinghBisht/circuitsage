#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / "backend" / ".venv" / "bin" / "python"
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv])
sys.path.insert(0, str(ROOT))

from backend.app.services.vectorstore import ingest, reset  # noqa: E402


KNOWLEDGE_ROOT = ROOT / "backend" / "app" / "knowledge"


def paragraphs(text: str) -> list[str]:
    return [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]


def topology_for(path: Path) -> str | None:
    name = path.stem.lower()
    if "op_amp" in name or "floating_noninv" in name:
        return "op_amp_inverting"
    if "rc" in name or "capacitor" in name:
        return "rc_lowpass"
    if "divider" in name or "load_resistance" in name:
        return "voltage_divider"
    if "bjt" in name or "2n3904" in name or "base_bias" in name:
        return "bjt_common_emitter"
    return None


def main() -> None:
    old_json = ROOT / "backend" / "app" / "data" / "vectorstore.json"
    if old_json.exists():
        old_json.unlink()
    reset()
    counts: dict[str, int] = {}
    for path in sorted(KNOWLEDGE_ROOT.rglob("*")):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        source = str(path.relative_to(KNOWLEDGE_ROOT))
        for index, text in enumerate(paragraphs(path.read_text(errors="ignore"))):
            doc_id = f"{source}#{index}"
            metadata = {"source": source, "paragraph": index}
            topology = topology_for(path)
            if topology:
                metadata["topology"] = topology
            ingest(doc_id, text, metadata)
            counts[source] = counts.get(source, 0) + 1
    for source, count in sorted(counts.items()):
        print(f"{source}: {count}")


if __name__ == "__main__":
    main()
