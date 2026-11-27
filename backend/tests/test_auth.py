import base64
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.auth import verify_access_token
from app.main import app

class _ActiveAccountStore:
    def __init__(self, _path):
        pass
    def identity_is_active(self, *, user_id, role):
        return True


KEY = "test-signing-key-that-is-at-least-32-bytes-long"
ISSUER = "speedy-live-auth"
AUDIENCE = "speedy-live-api"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_token(role: str, *, subject: str = "user-123", now: int = 2_000_000_000,
               expires: int = 2_000_000_300) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    claims = _b64(json.dumps({
        "sub": subject, "role": role, "iss": ISSUER, "aud": AUDIENCE,
        "iat": now, "exp": expires,
    }).encode())
    signing_input = f"{header}.{claims}".encode()
    signature = hmac.new(KEY.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{claims}.{_b64(signature)}"


def test_valid_customer_and_admin_tokens_produce_distinct_principals():
    assert verify_access_token(make_token("customer"), signing_key=KEY, issuer=ISSUER,
                               audience=AUDIENCE, now=2_000_000_001).role == "customer"
    assert verify_access_token(make_token("admin"), signing_key=KEY, issuer=ISSUER,
                               audience=AUDIENCE, now=2_000_000_001).role == "admin"


@pytest.mark.parametrize("changes", [
    {"role": "superuser"}, {"subject": ""}, {"expires": 2_000_000_000},
])
def test_invalid_claims_are_rejected(changes):
    values = {"role": "customer", "subject": "user-123", "expires": 2_000_000_300}
    values.update(changes)
    token = make_token(**values)
    with pytest.raises(ValueError):
        verify_access_token(token, signing_key=KEY, issuer=ISSUER,
                            audience=AUDIENCE, now=2_000_000_001)


def test_tampered_signature_is_rejected():
    token = make_token("admin")
    parts = token.split(".")
    parts[1] = _b64(json.dumps({"sub": "attacker", "role": "admin"}).encode())
    with pytest.raises(ValueError):
        verify_access_token(".".join(parts), signing_key=KEY, issuer=ISSUER,
                            audience=AUDIENCE, now=2_000_000_001)


def test_short_signing_key_is_rejected():
    with pytest.raises(ValueError, match="configured securely"):
        verify_access_token(make_token("admin"), signing_key="short",
                            issuer=ISSUER, audience=AUDIENCE, now=2_000_000_001)


def test_customer_cannot_access_admin_api_and_admin_cannot_access_customer_api(monkeypatch):
    monkeypatch.setattr(auth, "AccountStore", _ActiveAccountStore)
    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(
        auth_signing_key=KEY, auth_token_issuer=ISSUER, auth_token_audience=AUDIENCE
    ))
    client = TestClient(app)
    assert client.get("/admin/security/overview").status_code == 401
    current = int(time.time())
    customer = {"Authorization": f"Bearer {make_token('customer', now=current, expires=current + 300)}"}
    admin = {"Authorization": f"Bearer {make_token('admin', now=current, expires=current + 300)}"}
    assert client.get("/admin/security/overview", headers=customer).status_code == 403
    assert client.get("/customer/me", headers=admin).status_code == 403
    assert client.get("/admin/security/overview", headers=admin).json()["access"] == "administrator"
    assert client.get("/customer/me", headers=customer).json()["user_id"] == "user-123"
