from __future__ import annotations

import re
from pathlib import Path
from typing import Any


VALUE_MULTIPLIERS = {
    "": 1.0,
    "r": 1.0,
    "k": 1_000.0,
    "meg": 1_000_000.0,
    "m": 0.001,
}


def parse_spice_value(raw: str) -> float:
    match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)([a-zA-Z]*)", raw.strip())
    if not match:
        raise ValueError(f"Unsupported SPICE value: {raw}")
    number, suffix = match.groups()
    return float(number) * VALUE_MULTIPLIERS.get(suffix.lower(), 1.0)


def parse_netlist_text(text: str) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*") or stripped.startswith("."):
            continue
        parts = stripped.split()
        if len(parts) < 4:
            continue
        ref = parts[0]
        if ref.lower().startswith("r"):
            try:
                value_ohms = parse_spice_value(parts[3])
            except ValueError:
                continue
            components.append({"ref": ref, "value_ohms": value_ohms, "nodes": [parts[1], parts[2]]})

    rin = next((c for c in components if c["ref"].lower() == "rin"), None)
    rf = next((c for c in components if c["ref"].lower() == "rf"), None)

    if rin is None:
        rin = next((c for c in components if "vin" in c["nodes"] and "n_inv" in c["nodes"]), None)
    if rf is None:
        rf = next((c for c in components if "vout" in c["nodes"] and "n_inv" in c["nodes"]), None)

    detected_topology = "unknown"
    computed: dict[str, Any] = {}
    if rin and rf and rin["value_ohms"]:
        detected_topology = "op_amp_inverting"
        computed["gain"] = round(-(rf["value_ohms"] / rin["value_ohms"]), 3)

    return {
        "components": components,
        "detected_topology": detected_topology,
        "computed": computed,
    }


def parse_netlist_file(path: str | Path) -> dict[str, Any]:
    return parse_netlist_text(Path(path).read_text(errors="ignore"))

