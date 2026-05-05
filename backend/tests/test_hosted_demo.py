from fastapi.testclient import TestClient

from app import main


def test_hosted_demo_disables_native_companion(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "hosted_demo", True)
    with TestClient(main.app) as client:
        response = client.post("/api/companion/analyze", json={"question": "look at my screen"})
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"]


def test_hosted_demo_blocks_unseeded_writes(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "hosted_demo", True)
    with TestClient(main.app) as client:
        response = client.post("/api/sessions", json={"title": "public write", "student_level": "demo"})
    assert response.status_code == 403
    assert "read-only" in response.json()["detail"]


def test_hosted_demo_rate_limits_allowed_mutations(monkeypatch) -> None:
    main._hosted_rate_buckets.clear()
    monkeypatch.setattr(main.settings, "hosted_demo", True)
    monkeypatch.setattr(main.settings, "hosted_rate_limit_per_minute", 1)
    with TestClient(main.app) as client:
        first = client.post("/api/sessions/missing/diagnose", json={"message": "demo"})
        second = client.post("/api/sessions/missing/diagnose", json={"message": "demo"})
    assert first.status_code == 404
    assert second.status_code == 429
