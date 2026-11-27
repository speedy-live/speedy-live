import pytest
from app.account_store import AccountStore, AccountStoreError


def test_account_authentication_requires_verified_email(tmp_path):
    store = AccountStore(str(tmp_path / "accounts.sqlite3"))
    store.create_account(email="customer@example.test", password="correct horse battery", role="customer")
    assert store.authenticate(email="customer@example.test", password="correct horse battery") is None


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
