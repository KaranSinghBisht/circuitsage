from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_educator_overview_aggregates_demo_sessions() -> None:
    with TestClient(app) as client:
        client.post("/api/sessions/seed/op-amp")
        client.post("/api/sessions/seed/rc-lowpass")
        client.post("/api/sessions/seed/voltage-divider")
        response = client.get("/api/educator/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["total_sessions"] >= 3
    assert body["unfinished_sessions"] >= 0
    assert body["common_faults"]
    assert body["stalled_measurements"]
