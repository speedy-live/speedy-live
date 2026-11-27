from types import SimpleNamespace

import pytest

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
