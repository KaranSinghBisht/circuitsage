from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_agent_loop_executes_tool_and_sets_agentic_status(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    async def fake_chat(self, messages: list[dict[str, Any]], format_json: bool = False, tools=None) -> dict[str, Any]:
        calls["count"] += 1
        if calls["count"] == 1:
            return {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "request_measurement",
                            "arguments": json.dumps({"label": "V_noninv"}),
                        }
                    }
                ],
            }
        return {
            "content": json.dumps(
                {
                    "experiment_type": "unknown",
                    "expected_behavior": {},
                    "observed_behavior": {"summary": "Needs evidence", "evidence": []},
                    "likely_faults": [],
                    "next_measurement": {
                        "label": "V_noninv",
                        "expected": "topology-dependent",
                        "instruction": "Measure V_noninv.",
                    },
                    "safety": {"risk_level": "low_voltage_lab", "warnings": []},
                    "student_explanation": "Measure V_noninv next.",
                    "confidence": "low",
                }
            ),
            "tool_calls": [],
        }

    monkeypatch.setattr("app.services.agent_orchestrator.OllamaClient.chat", fake_chat)

    with TestClient(app) as client:
        session = client.post("/api/sessions", json={"title": "Agent loop test"}).json()
        response = client.post(f"/api/sessions/{session['id']}/diagnose", json={"message": "What should I measure?"})

    assert response.status_code == 200
    diagnosis = response.json()["diagnosis"]
    executed = [call for call in diagnosis["tool_calls"] if call["tool_name"] == "request_measurement" and call["status"] == "ok"]
    assert diagnosis["gemma_status"] == "ollama_gemma_agentic"
    assert diagnosis["agent_iterations"] == 2
    assert executed
    assert executed[-1]["output"] == {"requested": "V_noninv", "already_taken": False}
