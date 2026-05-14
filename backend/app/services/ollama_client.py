from __future__ import annotations

import json
from typing import Any

import httpx


class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        format_json: bool = False,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
        if format_json:
            payload["format"] = "json"

        fallback = False
        last_error: Exception | None = None
        # First attempt: long read window for cold-start vision calls (Modal can
        # take 60-120s on first model load). Second attempt: tight 30s ceiling
        # so a hung upstream can't hold the request handler for 10 minutes.
        timeouts = [
            httpx.Timeout(connect=5.0, read=300.0, write=30.0, pool=5.0),
            httpx.Timeout(connect=5.0, read=30.0, write=15.0, pool=5.0),
        ]
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=timeouts[attempt]) as client:
                    response = await client.post(f"{self.base_url}/api/chat", json=payload)
                    response.raise_for_status()
                    data = response.json()
                return {
                    "content": data.get("message", {}).get("content", ""),
                    "tool_calls": data.get("message", {}).get("tool_calls", []),
                    "raw_status": response.status_code,
                    "fallback": fallback,
                }
            except httpx.HTTPStatusError as exc:
                body = exc.response.text.lower()
                # Drop `tools` if the model truly rejected it. Match specific
                # phrases rather than any 'tools' substring (which always
                # appears in the body when we sent tools=...).
                tools_unsupported = any(
                    phrase in body
                    for phrase in ("does not support tools", "no tools", "tools not supported", "unknown field \"tools\"")
                )
                if exc.response.status_code in {400, 404, 500} and "tools" in payload and tools_unsupported:
                    payload.pop("tools", None)
                    fallback = True
                    continue
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
        # Bumped from 3s → 10s so a Modal-hosted Ollama mid-cold-start (5-60s
        # to spin up the container) doesn't show the user "model unavailable"
        # right after backend boot.
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
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
    """Best-effort extraction of the first top-level JSON object from `text`.

    Handles three common Gemma output shapes:
      1. Pure JSON ('{"a":1}') — fast path.
      2. JSON wrapped in code fences ('```json\\n{...}\\n```') — strip fences.
      3. Prose + JSON + trailing junk — brace-balanced scan from the first '{'
         picks the first complete object instead of the old over-greedy
         text.find('{') ... text.rfind('}') span which would mis-parse when
         the model emits multiple snippets.
    """
    if not text:
        return None
    candidate = text.strip()
    # Strip ```json ... ``` fences if present.
    if candidate.startswith("```"):
        candidate = candidate[3:]  # drop opening fence
        if candidate.lstrip().lower().startswith("json"):
            candidate = candidate.lstrip()[4:]
        end_fence = candidate.find("```")
        if end_fence >= 0:
            candidate = candidate[:end_fence]
        candidate = candidate.strip()
    try:
        result = json.loads(candidate)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        pass
    # Brace-balanced scan from the first '{' for the first complete object.
    start = candidate.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(candidate)):
        ch = candidate[idx]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    result = json.loads(candidate[start : idx + 1])
                    return result if isinstance(result, dict) else None
                except json.JSONDecodeError:
                    return None
    return None
