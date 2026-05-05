from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.database import db
from app.main import app


async def fail_ollama(*args: Any, **kwargs: Any) -> dict[str, Any]:
    raise RuntimeError("ollama disabled in test")


def test_chat_memory_reuses_prior_measurement_and_persists_tool_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.agent_orchestrator.OllamaClient.chat", fail_ollama)
    with TestClient(app) as client:
        seeded = client.post("/api/sessions/seed/op-amp").json()
        session_id = seeded["id"]

        first = client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "I already measured V_noninv at 2.8 V.", "mode": "bench"},
        )
        second = client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "What next?", "mode": "bench"},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    reply = second.json()["reply"].lower()
    assert "non-inverting" in reply
    assert "ground" in reply

    with db() as conn:
        row = conn.execute(
            """
            SELECT metadata_json FROM messages
            WHERE session_id = ? AND role = 'assistant'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()
    metadata = json.loads(row["metadata_json"])
    assert metadata["tool_calls"]
    assert metadata["tool_calls"][0]["tool_name"]
