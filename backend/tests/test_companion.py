from fastapi.testclient import TestClient

from app.main import app


def test_companion_analyze_returns_workspace_specific_fallback_without_image():
    with TestClient(app) as client:
        response = client.post(
            "/api/companion/analyze",
            json={
                "question": "I am in LTspice and my output is saturated near +12V. What should I check?",
                "app_hint": "ltspice",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["workspace"] == "ltspice"
    assert data["mode"] == "deterministic_fallback"
    assert data["next_actions"]


def test_companion_analyze_refuses_mains():
    with TestClient(app) as client:
        response = client.post(
            "/api/companion/analyze",
            json={"question": "I am probing a 230V AC mains circuit", "app_hint": "auto"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "safety_refusal"
    assert data["safety"]["risk_level"] == "high_voltage_or_mains"

