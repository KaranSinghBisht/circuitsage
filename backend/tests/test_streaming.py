from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import app
from app.services.streaming import add_sample, snapshot


def test_streaming_drift_detection_service() -> None:
    session_id = "stream-test"
    now = time.time()
    for index in range(12):
        add_sample(session_id, "Vout", 0 if index % 2 else 2.0, ts=now - 1 + index * 0.05)
    snap = snapshot(session_id)
    assert snap["events"]
    assert snap["events"][0]["type"] == "drift"


def test_streaming_endpoint_and_diagnosis_prioritizes_intermittent() -> None:
    with TestClient(app) as client:
        session = client.post("/api/sessions/seed/op-amp").json()
        for index in range(12):
            client.post(
                f"/api/sessions/{session['id']}/measurements/stream",
                json={"label": "Vout", "value": 0 if index % 2 else 2.0, "unit": "V"},
            )
        result = client.post(f"/api/sessions/{session['id']}/diagnose", json={"message": "The output jumps around."}).json()
    assert result["diagnosis"]["likely_faults"][0]["id"] == "intermittent_connection"
