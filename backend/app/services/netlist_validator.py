from __future__ import annotations

from typing import Any

from ..tools.parse_netlist import parse_netlist_text


def validate_netlist_text(netlist: str, confidence: float = 0.5, missing: list[str] | None = None) -> dict[str, Any]:
    parsed = parse_netlist_text(netlist)
    needed = list(missing or [])
    detected = parsed.get("detected_topology", "unknown")
    if detected == "unknown":
        needed.extend(["clear topology", "ground/reference node", "input/output labels"])
        confidence = min(confidence, 0.35)
    return {
        "netlist": netlist.strip(),
        "confidence": round(float(confidence), 3),
        "missing": sorted(set(item for item in needed if item)),
        "needed": sorted(set(item for item in needed if item)),
        "parsed": parsed,
        "detected_topology": detected,
    }
