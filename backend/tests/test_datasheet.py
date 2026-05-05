from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tools.datasheet import list_datasheets, lookup_datasheet


def test_datasheet_lookup_has_expanded_catalog() -> None:
    assert len(list_datasheets()) >= 20
    result = lookup_datasheet("2N3904")
    assert result["part_number"] == "2N3904"
    assert "pin" in result["pin_map"].lower()
    assert "common" not in result.get("error", "")


def test_datasheet_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/datasheets/IRLZ44N")
    assert response.status_code == 200
    body = response.json()
    assert body["part_number"] == "IRLZ44N"
    assert "Gate" in body["pin_map"] or "G-" in body["pin_map"]


def test_diagnosis_auto_detects_datasheets_from_netlist_models(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_ollama(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("ollama disabled in test")

    monkeypatch.setattr("app.services.agent_orchestrator.OllamaClient.chat", fail_ollama)

    netlist = """
V1 vcc 0 DC 5
Q1 vout base 0 2N3904
D1 vout clamp 1N4148
R1 vcc vout 2.2k
"""
    with TestClient(app) as client:
        session = client.post(
            "/api/sessions",
            json={"title": "Datasheet auto-detect", "experiment_type": "unknown"},
        ).json()
        artifact = client.post(f"/api/sessions/{session['id']}/artifacts/netlist", json={"netlist": netlist})
        response = client.post(f"/api/sessions/{session['id']}/diagnose", json={"message": "Check the transistor clamp."})

    assert artifact.status_code == 200
    assert response.status_code == 200
    lookup_calls = [call for call in response.json()["tool_calls"] if call["tool_name"] == "lookup_datasheet"]
    looked_up_parts = {call["input"]["part_number"] for call in lookup_calls}
    assert {"2N3904", "1N4148"} <= looked_up_parts
    assert len(lookup_calls) <= 3
