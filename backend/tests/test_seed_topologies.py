from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app


async def fail_ollama(*args: Any, **kwargs: Any) -> dict[str, Any]:
    raise RuntimeError("ollama disabled in test")


@pytest.mark.parametrize(
    ("slug", "topology", "fault_id"),
    [
        ("rc-lowpass", "rc_lowpass", "wrong_capacitor_value"),
        ("voltage-divider", "voltage_divider", "load_resistance_too_low"),
        ("bjt-common-emitter", "bjt_common_emitter", "incorrect_base_bias"),
        ("op-amp-noninverting", "op_amp_noninverting", "rg_open"),
    ],
)
def test_seed_endpoint_returns_catalog_diagnosis(
    monkeypatch: pytest.MonkeyPatch,
    slug: str,
    topology: str,
    fault_id: str,
) -> None:
    monkeypatch.setattr("app.services.agent_orchestrator.OllamaClient.chat", fail_ollama)
    with TestClient(app) as client:
        response = client.post(f"/api/sessions/seed/{slug}")

    assert response.status_code == 200
    data = response.json()
    diagnosis = data["seed_diagnosis"]
    assert data["experiment_type"] == topology
    assert diagnosis["gemma_status"] == "deterministic_fallback"
    assert diagnosis["likely_faults"][0]["id"] == fault_id
    assert "floating" not in diagnosis["student_explanation"].lower()
