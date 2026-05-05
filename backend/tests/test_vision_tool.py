from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.tools.vision import describe_artifact


@pytest.mark.anyio
async def test_describe_artifact_sends_image_prompt_and_parses_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    image = tmp_path / "breadboard.png"
    image.write_bytes(b"fake-image")
    captured: dict[str, Any] = {}

    async def fake_chat(self, messages: list[dict[str, Any]], format_json: bool = False, tools=None) -> dict[str, Any]:
        captured["messages"] = messages
        captured["format_json"] = format_json
        return {
            "content": '{"artifact_kind":"breadboard","visible_components":["op amp"],"topology_hint":"op_amp_inverting"}',
            "tool_calls": [],
            "raw_status": 200,
            "fallback": False,
        }

    monkeypatch.setattr("app.tools.vision.OllamaClient.chat", fake_chat)
    result = await describe_artifact(
        {"id": "a1", "kind": "breadboard", "filename": "breadboard.png", "path": str(image)},
        "http://ollama.local",
        "gemma3:4b",
    )

    assert result["mode"] == "ollama_gemma_vision"
    assert result["artifact_kind"] == "breadboard"
    assert captured["format_json"] is False
    assert captured["messages"][0]["images"]
    assert "Artifact kind hint: breadboard" in captured["messages"][0]["content"]
