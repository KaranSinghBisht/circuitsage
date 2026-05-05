from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_report_pdf_endpoint_opens_with_pdf_header() -> None:
    with TestClient(app) as client:
        seeded = client.post("/api/sessions/seed/op-amp").json()
        response = client.get(f"/api/sessions/{seeded['id']}/report.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 2000
