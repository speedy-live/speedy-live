import base64
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import Settings

TEST_KEY = "test-signing-key-that-is-at-least-32-bytes-long"


def _token(role="customer"):
    def enc(value):
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode()
    header = enc(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    claims = enc(json.dumps({
        "sub": "test-user", "role": role, "iss": "speedy-live-auth",
        "aud": "speedy-live-api", "iat": int(time.time()), "exp": int(time.time()) + 300,
    }).encode())
    signature = hmac.new(TEST_KEY.encode(), f"{header}.{claims}".encode(), hashlib.sha256).digest()
    return f"{header}.{claims}.{enc(signature)}"


@pytest.mark.parametrize(
    ("approved", "approval_id", "expected"),
    [(False, "", False), (True, "", False), (False, "release-review-001", False),
     (True, "release-review-001", True)],
)
def test_customer_animation_requires_explicit_release_approval(
    monkeypatch, approved, approval_id, expected
):
    monkeypatch.setattr(
        main, "settings",
        Settings(animation_engine_customer_release_approved=approved,
                 animation_engine_release_approval_id=approval_id),
    )
    monkeypatch.setattr(main, "engine_registry", SimpleNamespace(operational=True))
    assert main.customer_animation_is_enabled() is expected


def test_runtime_health_alone_never_enables_customer_animation(monkeypatch):
    monkeypatch.setattr(
        main, "settings",
        Settings(animation_engine_customer_release_approved=True,
                 animation_engine_release_approval_id="release-review-001"),
    )
    monkeypatch.setattr(main, "engine_registry", SimpleNamespace(operational=False))
    assert main.customer_animation_is_enabled() is False


def test_capabilities_endpoint_stays_blocked_without_release_approval(monkeypatch):
    monkeypatch.setattr(main, "settings", Settings())
    monkeypatch.setattr(
        main, "engine_registry",
        SimpleNamespace(operational=True, status=lambda: {
            "configured": True, "runtime_healthy": True, "operational": True,
            "engine_id": "test-engine",
        }),
    )
    response = TestClient(main.app).get(
        "/engine/capabilities/full_body",
        headers={"Authorization": f"Bearer {_token('customer')}"},
    )
    assert response.status_code == 503
    assert "explicit release approval" in response.json()["detail"]


def test_engine_status_is_admin_only_and_does_not_claim_customer_release(monkeypatch):
    monkeypatch.setattr(main, "settings", Settings())
    monkeypatch.setattr(
        main, "engine_registry",
        SimpleNamespace(operational=True, status=lambda: {
            "configured": True, "runtime_healthy": True, "operational": True,
            "engine_id": "test-engine", "message": "Engine passed its runtime self-test.",
        }),
    )
    client = TestClient(main.app)
    assert client.get("/engine/status").status_code == 401
    customer = client.get("/engine/status", headers={
        "Authorization": f"Bearer {_token('customer')}"
    })
    assert customer.status_code == 403
    response = client.get("/engine/status", headers={
        "Authorization": f"Bearer {_token('admin')}"
    })
    assert response.status_code == 200
    assert response.json()["operational"] is True
    assert response.json()["customer_release_approved"] is False
    assert response.json()["customer_animation_enabled"] is False
    assert "customer use remains disabled" in response.json()["message"]


def test_public_readiness_does_not_expose_internal_engine_metadata():
    response = TestClient(main.app).get("/ready")
    assert response.status_code == 200
    assert "engine" not in response.json()
