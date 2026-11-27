import pytest
from types import SimpleNamespace
from fastapi.testclient import TestClient
from app import auth, main
from app.account_store import AccountStore, AccountStoreError


def test_account_authentication_requires_verified_email(tmp_path):
    store = AccountStore(str(tmp_path / "accounts.sqlite3"))
    store.create_account(email="customer@example.test", password="correct horse battery", role="customer")
    assert store.authenticate(email="customer@example.test", password="correct horse battery") is None


def test_admin_does_not_require_customer_email_verification(tmp_path):
    store = AccountStore(str(tmp_path / "accounts.sqlite3"))
    user_id = store.create_account(email="admin@example.test", password="correct horse battery",
                                   role="admin", email_verified=False)
    identity = store.authenticate(email="admin@example.test", password="correct horse battery")
    assert identity == {"user_id": user_id, "role": "admin", "email": "admin@example.test"}
    assert store.identity_is_active(user_id=user_id, role="admin")


def test_verified_customer_can_authenticate_and_role_is_store_controlled(tmp_path):
    store = AccountStore(str(tmp_path / "accounts.sqlite3"))
    user_id = store.create_account(email="customer@example.test", password="correct horse battery",
                                   role="customer", email_verified=True)
    identity = store.authenticate(email="CUSTOMER@example.test", password="correct horse battery")
    assert identity == {"user_id": user_id, "role": "customer", "email": "customer@example.test"}
    assert store.identity_is_active(user_id=user_id, role="customer")
    assert not store.identity_is_active(user_id=user_id, role="admin")


def test_wrong_password_and_unknown_email_are_rejected(tmp_path):
    store = AccountStore(str(tmp_path / "accounts.sqlite3"))
    store.create_account(email="customer@example.test", password="correct horse battery",
                         role="customer", email_verified=True)
    assert store.authenticate(email="customer@example.test", password="wrong password") is None
    assert store.authenticate(email="unknown@example.test", password="wrong password") is None


def test_invalid_role_is_rejected(tmp_path):
    store = AccountStore(str(tmp_path / "accounts.sqlite3"))
    with pytest.raises(ValueError, match="Invalid role"):
        store.create_account(email="customer@example.test", password="correct horse battery", role="superuser")


def test_duplicate_email_is_rejected(tmp_path):
    store = AccountStore(str(tmp_path / "accounts.sqlite3"))
    store.create_account(email="customer@example.test", password="correct horse battery",
                         role="customer", email_verified=True)
    with pytest.raises(AccountStoreError, match="Email already exists"):
        store.create_account(email="CUSTOMER@example.test", password="another secure password",
                             role="customer", email_verified=True)



def test_login_issues_role_scoped_token_only_for_verified_account(tmp_path, monkeypatch):
    database = str(tmp_path / "accounts.sqlite3")
    store = AccountStore(database)
    store.create_account(email="customer@example.test", password="correct horse battery",
                         role="customer", email_verified=True)
    admin_id = store.create_account(email="admin@example.test", password="another secure password",
                                    role="admin", email_verified=True)
    settings = SimpleNamespace(
        environment="development",
        auth_database_path=database,
        auth_signing_key="test-signing-key-that-is-at-least-32-bytes-long",
        auth_token_issuer="speedy-live-auth",
        auth_token_audience="speedy-live-api",
    )
    monkeypatch.setattr(main, "settings", settings)
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    client = TestClient(main.app)
    denied = client.post("/auth/login", json={
        "email": "notverified@example.test", "password": "correct horse battery"
    })
    assert denied.status_code == 401
    customer = client.post("/auth/login", json={
        "email": "customer@example.test", "password": "correct horse battery"
    })
    assert customer.status_code == 200
    assert customer.json()["user"]["role"] == "customer"
    customer_token = customer.json()["access_token"]
    assert client.get("/admin/auth/me", headers={
        "Authorization": f"Bearer {customer_token}"
    }).status_code == 403
    admin = client.post("/auth/login", json={
        "email": "admin@example.test", "password": "another secure password"
    })
    assert admin.status_code == 200
    assert admin.json()["user"]["id"] == admin_id
    admin_token = admin.json()["access_token"]
    assert client.get("/admin/auth/me", headers={
        "Authorization": f"Bearer {admin_token}"
    }).json()["role"] == "admin"
    assert client.get("/auth/me", headers={
        "Authorization": f"Bearer {admin_token}"
    }).status_code == 403
