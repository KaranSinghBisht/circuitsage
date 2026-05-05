from __future__ import annotations

import json
from typing import Any

import httpx


class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def chat(self, messages: list[dict[str, Any]], format_json: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if format_json:
            payload["format"] = "json"

        fallback = False
        last_error: Exception | None = None
        timeout = httpx.Timeout(connect=5.0, read=120.0, write=30.0, pool=5.0)
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(f"{self.base_url}/api/chat", json=payload)
                    response.raise_for_status()
                    data = response.json()
                return {
                    "content": data.get("message", {}).get("content", ""),
                    "raw_status": response.status_code,
                    "fallback": fallback,
                }
            except httpx.HTTPStatusError as exc:
                body = exc.response.text.lower()
                if format_json and exc.response.status_code in {400, 500} and "format" in body and "format" in payload:
                    payload.pop("format", None)
                    fallback = True
                    continue
                raise
            except (httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
                last_error = exc
                if attempt == 0:
                    continue
                raise
        raise last_error or RuntimeError("Ollama chat failed")

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                models = response.json().get("models", [])
                model_names = [m.get("name") for m in models]
                show = await client.post(f"{self.base_url}/api/show", json={"name": self.model})
            loaded = show.status_code == 200
            result = {"available": True, "model": self.model, "loaded": loaded, "models": model_names}
            if not loaded:
                result["hint"] = f"Run: ollama pull {self.model}"
            return result
        except Exception as exc:  # noqa: BLE001 - endpoint should surface a clean status.
            return {
                "available": False,
                "model": self.model,
                "loaded": False,
                "models": [],
                "hint": f"Run: ollama pull {self.model}",
                "error": str(exc),
            }


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
