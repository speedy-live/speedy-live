from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import Settings


@pytest.mark.parametrize(
    ("approved", "approval_id", "expected"),
    [
        (False, "", False),
        (True, "", False),
        (False, "release-review-001", False),
        (True, "release-review-001", True),
    ],
)
def test_customer_animation_requires_explicit_release_approval(
    monkeypatch, approved, approval_id, expected
):
    monkeypatch.setattr(
        main,
        "settings",
        Settings(
            animation_engine_customer_release_approved=approved,
            animation_engine_release_approval_id=approval_id,
        ),
    )
    monkeypatch.setattr(main, "engine_registry", SimpleNamespace(operational=True))

    assert main.customer_animation_is_enabled() is expected


def test_runtime_health_alone_never_enables_customer_animation(monkeypatch):
    monkeypatch.setattr(
        main,
        "settings",
        Settings(
            animation_engine_customer_release_approved=True,
            animation_engine_release_approval_id="release-review-001",
        ),
    )
    monkeypatch.setattr(main, "engine_registry", SimpleNamespace(operational=False))

    assert main.customer_animation_is_enabled() is False


def test_capabilities_endpoint_stays_blocked_without_release_approval(monkeypatch):
    monkeypatch.setattr(main, "settings", Settings())
    monkeypatch.setattr(
        main,
        "engine_registry",
        SimpleNamespace(
            operational=True,
            status=lambda: {
                "configured": True,
                "runtime_healthy": True,
                "operational": True,
                "engine_id": "test-engine",
            },
        ),
    )

    response = TestClient(main.app).get("/engine/capabilities/full_body")

    assert response.status_code == 503
    assert "explicit release approval" in response.json()["detail"]


def test_engine_status_does_not_report_customer_enabled_without_approval(monkeypatch):
    monkeypatch.setattr(main, "settings", Settings())
    monkeypatch.setattr(
        main,
        "engine_registry",
        SimpleNamespace(
            operational=True,
            status=lambda: {
                "configured": True,
                "runtime_healthy": True,
                "operational": True,
                "engine_id": "test-engine",
                "message": "Engine passed its runtime self-test.",
            },
        ),
    )

    response = TestClient(main.app).get("/engine/status")

    assert response.status_code == 200
    assert response.json()["operational"] is True
    assert response.json()["customer_release_approved"] is False
    assert response.json()["customer_animation_enabled"] is False
    assert "customer use remains disabled" in response.json()["message"]
