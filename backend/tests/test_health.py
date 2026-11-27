from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_does_not_claim_animation_is_available() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["animation_engine_configured"] is False
    assert body["status"] == "not_ready"
