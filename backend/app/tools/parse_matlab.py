from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _non_comment_lines(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("%"):
            lines.append(stripped)
    return lines


def parse_matlab_text(text: str) -> dict[str, Any]:
    context_lines = _non_comment_lines(text)[:50]
    context = "\n".join(context_lines)
    assignments = []
    sampling_rate_hz = None
    for name, value in re.findall(r"^\s*([A-Za-z]\w*)\s*=\s*(.+?);?\s*$", context, flags=re.MULTILINE):
        assignments.append({"name": name, "value": value.rstrip(";")})
        if name.lower() in {"fs", "sample_rate", "sampling_rate"}:
            try:
                sampling_rate_hz = float(value.rstrip(";"))
            except ValueError:
                sampling_rate_hz = None
    return {
        "assignments": assignments,
        "plot_calls": [{"args": args.strip()} for args in re.findall(r"\bplot\s*\(([^)]*)\)", context)],
        "sampling_rate_hz": sampling_rate_hz,
        "context_lines": context_lines,
    }


def parse_matlab_file(path: str | Path) -> dict[str, Any]:
    return parse_matlab_text(Path(path).read_text(errors="ignore"))
