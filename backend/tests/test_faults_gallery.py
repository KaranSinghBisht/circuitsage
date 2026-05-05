from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_faults_gallery_lists_catalog_and_seeds_fault() -> None:
    with TestClient(app) as client:
        faults = client.get("/api/faults").json()
        assert len(faults) >= 18
        assert len({fault["topology"] for fault in faults}) >= 6
        first = next(fault for fault in faults if fault["topology"] == "op_amp_inverting")
        seeded = client.post(f"/api/sessions/seed/fault/{first['topology']}/{first['id']}")
    assert seeded.status_code == 200
    body = seeded.json()
    assert body["experiment_type"] == first["topology"]
    assert body["latest_diagnosis"]["likely_faults"]
