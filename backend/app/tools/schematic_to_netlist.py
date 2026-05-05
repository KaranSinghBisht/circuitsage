from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..services.netlist_validator import validate_netlist_text
from ..services.ollama_client import OllamaClient, parse_json_response

PROMPT = """You are a circuit-recognition assistant. Convert the visible schematic
to a minimal SPICE netlist with these rules:
- Use refs Rin / Rf / R1..Rn / C1..Cn / Q1..Qn / D1..Dn etc.
- Use nodes vin, vout, n_inv, n_noninv, vcc, vee, gnd (alias 0).
- Use SI suffixes: k, meg, n, u.
- Skip components you cannot see clearly.
Return JSON: {"netlist": "...", "confidence": 0..1, "missing": ["..."]}."""


def image_file_to_base64(path: str | Path) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


async def recognize_schematic(image_b64: str, *, hint: str = "") -> dict[str, Any]:
    settings = get_settings()
    try:
        result = await OllamaClient(settings.ollama_base_url, settings.ollama_vision_model).chat(
            [{"role": "user", "content": f"{PROMPT}\n\nHint: {hint}", "images": [image_b64]}],
            format_json=True,
        )
        parsed = parse_json_response(result["content"]) or {}
        netlist = str(parsed.get("netlist", "")).strip()
        confidence = float(parsed.get("confidence", 0.0) or 0.0)
        missing = [str(item) for item in parsed.get("missing", []) if str(item).strip()]
        if not netlist:
            return validate_netlist_text("", confidence=0.0, missing=missing or ["visible components"])
        validated = validate_netlist_text(netlist, confidence=confidence, missing=missing)
        validated["mode"] = "ollama_gemma_vision"
        return validated
    except Exception as exc:  # noqa: BLE001 - no silent fabrication when vision is unavailable.
        result = validate_netlist_text("", confidence=0.0, missing=["vision model unavailable", "schematic photo"])
        result["mode"] = "vision_unavailable"
        result["error"] = f"{exc.__class__.__name__}: {exc}"
        return result
