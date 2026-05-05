from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import SEED_TO_TOPOLOGY, app
from app.tools.parse_netlist import parse_netlist_file


def test_new_topology_pack_netlists_detect() -> None:
    root = Path("sample_data")
    for topology in SEED_TO_TOPOLOGY.values():
        parsed = parse_netlist_file(root / topology / "netlist.net")
        assert parsed["detected_topology"] == topology


def test_new_topology_pack_seed_endpoints() -> None:
    with TestClient(app) as client:
        for slug, topology in SEED_TO_TOPOLOGY.items():
            response = client.post(f"/api/sessions/seed/{slug}")
            assert response.status_code == 200, slug
            body = response.json()
            assert body["experiment_type"] == topology
            assert body["latest_diagnosis"]["experiment_type"] == topology
            assert body["latest_diagnosis"]["likely_faults"]
