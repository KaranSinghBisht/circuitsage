from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.fault_catalog import CATALOG


SEED_CASES = [
    ("op-amp", "op_amp_inverting"),
    ("rc-lowpass", "rc_lowpass"),
    ("voltage-divider", "voltage_divider"),
    ("bjt-common-emitter", "bjt_common_emitter"),
    ("op-amp-noninverting", "op_amp_noninverting"),
    ("full-wave-rectifier", "full_wave_rectifier"),
    ("active-highpass", "active_highpass_filter"),
    ("integrator", "op_amp_integrator"),
    ("differentiator", "op_amp_differentiator"),
    ("schmitt-trigger", "schmitt_trigger"),
    ("timer-555-astable", "timer_555_astable"),
    ("nmos-low-side", "nmos_low_side_switch"),
    ("instrumentation-amplifier", "instrumentation_amplifier"),
]
ALLOWED_GEMMA_STATUSES = {"deterministic_fallback", "ollama_gemma_agentic", "ollama_gemma_single_shot"}


async def fail_ollama(*args: Any, **kwargs: Any) -> dict[str, Any]:
    raise RuntimeError("ollama disabled in topology-pack test")


@pytest.mark.parametrize(("slug", "topology"), SEED_CASES, ids=[topology for _, topology in SEED_CASES])
def test_seed_endpoint_returns_catalog_fault_for_topology(
    monkeypatch: pytest.MonkeyPatch,
    slug: str,
    topology: str,
) -> None:
    monkeypatch.setattr("app.services.agent_orchestrator.OllamaClient.chat", fail_ollama)
    with TestClient(app) as client:
        response = client.post(f"/api/sessions/seed/{slug}")

    assert response.status_code == 200, slug
    body = response.json()
    diagnosis = body["seed_diagnosis"]
    catalog_fault_ids = {fault["id"] for fault in CATALOG[topology]["faults"]}
    returned_fault_ids = {fault.get("id") for fault in diagnosis["likely_faults"]}

    assert body["experiment_type"] == topology
    assert diagnosis["experiment_type"] == topology
    assert diagnosis["gemma_status"] in ALLOWED_GEMMA_STATUSES
    assert returned_fault_ids & catalog_fault_ids
