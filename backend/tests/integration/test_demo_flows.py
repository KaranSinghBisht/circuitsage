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


async def fail_ollama(*args: Any, **kwargs: Any) -> dict[str, Any]:
    raise RuntimeError("ollama disabled in integration test")


@pytest.mark.parametrize(("slug", "topology"), SEED_CASES, ids=[topology for _, topology in SEED_CASES])
def test_seed_to_report_flow_for_topology(
    monkeypatch: pytest.MonkeyPatch,
    slug: str,
    topology: str,
) -> None:
    monkeypatch.setattr("app.services.agent_orchestrator.OllamaClient.chat", fail_ollama)
    catalog_top_fault = CATALOG[topology]["faults"][0]
    measurement_label = (catalog_top_fault.get("requires_measurements") or ["observed_node"])[0]

    with TestClient(app) as client:
        seed = client.post(f"/api/sessions/seed/{slug}")
        assert seed.status_code == 200, seed.text
        session = seed.json()
        session_id = session["id"]

        artifacts = client.get(f"/api/sessions/{session_id}/artifacts")
        assert artifacts.status_code == 200, artifacts.text
        assert artifacts.json()

        measurement = client.post(
            f"/api/sessions/{session_id}/measurements",
            json={
                "label": measurement_label,
                "value": 1.0,
                "unit": "V",
                "mode": "DC",
                "context": f"Integration measurement for {catalog_top_fault['name']}",
            },
        )
        assert measurement.status_code == 200, measurement.text

        diagnosis_response = client.post(
            f"/api/sessions/{session_id}/diagnose",
            json={"message": f"Run the full demo flow for {topology}."},
        )
        assert diagnosis_response.status_code == 200, diagnosis_response.text
        diagnosis = diagnosis_response.json()["diagnosis"]

        generated_report = client.post(f"/api/sessions/{session_id}/report")
        assert generated_report.status_code == 200, generated_report.text

        report = client.get(f"/api/sessions/{session_id}/report")
        assert report.status_code == 200, report.text
        assert report.json()["markdown"]

        pdf = client.get(f"/api/sessions/{session_id}/report.pdf")
        assert pdf.status_code == 200, pdf.text
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.content.startswith(b"%PDF")

    returned_fault_ids = {fault.get("id") for fault in diagnosis["likely_faults"]}
    assert diagnosis["experiment_type"] == topology
    assert catalog_top_fault["id"] in returned_fault_ids
