from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_reports_service() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "speedy-live-ai"


def test_readiness_does_not_claim_unconfigured_engine_is_ready() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "not_ready"
    assert response.json()["animation_engine_configured"] is False


def test_motion_diagnostics_returns_timing_and_coverage() -> None:
    response = client.post(
        "/motion/diagnostics",
        json=[
            {
                "sequence": 0,
                "timestamp_ms": 0,
                "body_landmarks": [{"x": 0.5, "y": 0.4}],
                "face": {"blendshapes": {"eyeBlinkLeft": 0.1}},
            },
            {
                "sequence": 1,
                "timestamp_ms": 40,
                "body_landmarks": [{"x": 0.6, "y": 0.4}],
                "face": {"blendshapes": {"eyeBlinkLeft": 1.0}},
            },
        ],
    )
    assert response.status_code == 200
    result = response.json()
    assert result["sample_count"] == 2
    assert result["duration_ms"] == 40
    assert result["estimated_fps"] == 25
    assert result["body_point_count"] == 2
    assert result["face_sample_count"] == 2


def test_motion_diagnostics_rejects_duplicate_timestamps() -> None:
    frame = {"sequence": 0, "timestamp_ms": 12, "body_landmarks": []}
    response = client.post("/motion/diagnostics", json=[frame, frame])
    assert response.status_code == 422
    assert "sequence" in response.json()["detail"]


def test_motion_diagnostics_rejects_oversized_batch() -> None:
    response = client.post(
        "/motion/diagnostics",
        json=[{"sequence": i, "timestamp_ms": i, "body_landmarks": []} for i in range(3001)],
    )
    assert response.status_code == 422


def test_api_responses_include_browser_security_headers() -> None:
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == (
        "camera=(self), microphone=(self), geolocation=()"
    )


def test_api_does_not_send_hsts_for_local_development() -> None:
    response = client.get("/health")
    assert "strict-transport-security" not in response.headers
