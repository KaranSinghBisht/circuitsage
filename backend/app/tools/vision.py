from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from ..services.ollama_client import OllamaClient, parse_json_response


VISION_PROMPT = """Inspect this low-voltage electronics lab image.

Return compact JSON if possible:
{
  "artifact_kind": "breadboard | oscilloscope | schematic | unknown",
  "visible_components": ["..."],
  "readable_labels": ["..."],
  "topology_hint": "op_amp_inverting | rc_lowpass | voltage_divider | bjt_common_emitter | unknown",
  "possible_fault_evidence": ["..."],
  "uncertainty": "low | medium | high"
}

Only state visible evidence. Do not invent component values."""


async def describe_artifact(artifact: dict[str, Any], base_url: str, model: str) -> dict[str, Any]:
    path = Path(artifact["path"])
    image_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    try:
        result = await OllamaClient(base_url, model).chat(
            [
                {
                    "role": "user",
                    "content": f"{VISION_PROMPT}\n\nArtifact kind hint: {artifact.get('kind', 'image')}",
                    "images": [image_b64],
                }
            ],
            format_json=False,
        )
        content = result["content"]
        parsed = parse_json_response(content) or {"raw": content[:1200]}
        return {
            "artifact_id": artifact.get("id"),
            "filename": artifact.get("filename"),
            "mode": "ollama_gemma_vision",
            **parsed,
        }
    except Exception as exc:  # noqa: BLE001 - diagnosis must keep running without vision model.
        return {
            "artifact_id": artifact.get("id"),
            "filename": artifact.get("filename"),
            "mode": "deterministic_vision_fallback",
            "artifact_kind": artifact.get("kind", "image"),
            "visible_components": [],
            "readable_labels": [],
            "topology_hint": "unknown",
            "possible_fault_evidence": [],
            "uncertainty": "high",
            "error": exc.__class__.__name__,
        }
