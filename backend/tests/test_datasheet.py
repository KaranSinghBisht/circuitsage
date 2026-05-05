from __future__ import annotations

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
