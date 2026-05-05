from fastapi.testclient import TestClient
import base64

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


def test_companion_uses_source_title_for_workspace_guess():
    with TestClient(app) as client:
        response = client.post(
            "/api/companion/analyze",
            json={
                "question": "What should I check next?",
                "app_hint": "auto",
                "source_title": "Draft1.asc - LTspice XVII",
            },
        )
    assert response.status_code == 200
    assert response.json()["workspace"] == "ltspice"


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


def test_companion_analyze_uses_two_step_vision_flow(monkeypatch):
    calls = []

    async def fake_chat(self, messages, format_json=False, tools=None):
        calls.append({"messages": messages, "format_json": format_json})
        if len(calls) == 1:
            return {"content": "I can see an LTspice waveform and the output is clipped.", "tool_calls": []}
        return {
            "content": (
                '{"workspace":"ltspice","visible_context":"clipped waveform",'
                '"answer":"Check rails and probe reference.",'
                '"next_actions":["Measure Vout DC","Check ground"],'
                '"can_click":false,"safety":{"risk_level":"low_voltage_lab","warnings":[]},'
                '"confidence":"medium"}'
            ),
            "tool_calls": [],
        }

    monkeypatch.setattr("app.main.OllamaClient.chat", fake_chat)
    image = "data:image/jpeg;base64," + base64.b64encode(b"fake").decode("ascii")

    with TestClient(app) as client:
        response = client.post(
            "/api/companion/analyze",
            json={"question": "What is wrong?", "app_hint": "ltspice", "image_data_url": image},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "ollama_gemma_vision"
    assert calls[0]["format_json"] is False
    assert calls[0]["messages"][0]["images"]
    assert calls[1]["format_json"] is True
    assert "images" not in calls[1]["messages"][0]
