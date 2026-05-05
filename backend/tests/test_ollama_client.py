from __future__ import annotations

from copy import deepcopy
from typing import Any

import httpx
import pytest

from app.services.ollama_client import OllamaClient


class FakeAsyncClient:
    calls: list[dict[str, Any]] = []
    responses: list[Any] = []

    def __init__(self, *args: Any, **kwargs: Any):
        self.args = args
        self.kwargs = kwargs

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def post(self, url: str, json: dict[str, Any]) -> httpx.Response:
        self.__class__.calls.append({"url": url, "json": deepcopy(json)})
        next_response = self.__class__.responses.pop(0)
        if isinstance(next_response, Exception):
            raise next_response
        return next_response


def response(status_code: int, payload: dict[str, Any] | None = None, text: str | None = None) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=payload,
        text=text,
        request=httpx.Request("POST", "http://ollama.local/api/chat"),
    )


@pytest.fixture(autouse=True)
def fake_async_client(monkeypatch: pytest.MonkeyPatch) -> type[FakeAsyncClient]:
    FakeAsyncClient.calls = []
    FakeAsyncClient.responses = []
    monkeypatch.setattr("app.services.ollama_client.httpx.AsyncClient", FakeAsyncClient)
    return FakeAsyncClient


@pytest.mark.anyio
async def test_chat_success_path(fake_async_client: type[FakeAsyncClient]) -> None:
    fake_async_client.responses = [response(200, {"message": {"content": "ok"}})]

    result = await OllamaClient("http://ollama.local", "gemma3:4b").chat([{"role": "user", "content": "hi"}])

    assert result == {"content": "ok", "raw_status": 200, "fallback": False}
    assert fake_async_client.calls[0]["json"]["model"] == "gemma3:4b"


@pytest.mark.anyio
async def test_chat_retries_read_timeout_once(fake_async_client: type[FakeAsyncClient]) -> None:
    fake_async_client.responses = [
        httpx.ReadTimeout("slow generation"),
        response(200, {"message": {"content": "after retry"}}),
    ]

    result = await OllamaClient("http://ollama.local", "gemma3:4b").chat([{"role": "user", "content": "hi"}])

    assert result["content"] == "after retry"
    assert len(fake_async_client.calls) == 2


@pytest.mark.anyio
async def test_chat_retries_without_format_when_ollama_rejects_json_format(
    fake_async_client: type[FakeAsyncClient],
) -> None:
    fake_async_client.responses = [
        response(400, text="unknown format json"),
        response(200, {"message": {"content": "{\"ok\": true}"}}),
    ]

    result = await OllamaClient("http://ollama.local", "gemma3:4b").chat(
        [{"role": "user", "content": "json please"}],
        format_json=True,
    )

    assert result["fallback"] is True
    assert "format" in fake_async_client.calls[0]["json"]
    assert "format" not in fake_async_client.calls[1]["json"]


@pytest.mark.anyio
async def test_chat_does_not_retry_non_format_4xx(fake_async_client: type[FakeAsyncClient]) -> None:
    fake_async_client.responses = [response(404, text="model not found")]

    with pytest.raises(httpx.HTTPStatusError):
        await OllamaClient("http://ollama.local", "missing-model").chat([{"role": "user", "content": "hi"}])

    assert len(fake_async_client.calls) == 1
