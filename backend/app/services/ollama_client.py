from __future__ import annotations

import json
from typing import Any

import httpx


class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def chat(self, messages: list[dict[str, Any]], format_json: bool = False) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if format_json:
            payload["format"] = "json"
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        return data.get("message", {}).get("content", "")

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                models = response.json().get("models", [])
            return {"available": True, "model": self.model, "models": [m.get("name") for m in models]}
        except Exception as exc:  # noqa: BLE001 - endpoint should surface a clean status.
            return {"available": False, "model": self.model, "error": str(exc)}


def parse_json_response(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None
