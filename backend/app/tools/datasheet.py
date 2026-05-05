from __future__ import annotations

from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "datasheets"


def _clean(part_number: str) -> str:
    return part_number.upper().replace("-", "").replace("_", "")


def _parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = "summary"
    chunks: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            sections[current] = "\n".join(chunks).strip()
            current = line[3:].strip().lower().replace(" ", "_")
            chunks = []
        elif not line.startswith("# "):
            chunks.append(line)
    sections[current] = "\n".join(chunks).strip()
    return sections


def lookup_datasheet(part_number: str) -> dict[str, Any]:
    wanted = _clean(part_number)
    for path in sorted(DATA_DIR.glob("*.md")):
        if _clean(path.stem) == wanted:
            text = path.read_text(errors="ignore")
            sections = _parse_sections(text)
            return {
                "part_number": path.stem.upper(),
                "summary": sections.get("summary", "").strip(),
                "pin_map": sections.get("pin_map", sections.get("summary", "")),
                "abs_max": sections.get("absolute_maximums", ""),
                "typical_use": sections.get("typical_use", ""),
                "common_faults": sections.get("common_faults", ""),
                "source": str(path.relative_to(DATA_DIR.parents[2])),
            }
    return {
        "part_number": part_number,
        "error": "datasheet_not_found",
        "available": sorted(path.stem.upper() for path in DATA_DIR.glob("*.md")),
    }


def list_datasheets() -> list[str]:
    return sorted(path.stem.upper() for path in DATA_DIR.glob("*.md"))
