import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_accepts_explicit_https_origins():
    settings = Settings(
        environment="production",
        allowed_origins="https://speedy-live.pages.dev,https://www.example.test",
    )
    assert settings.cors_origins == [
        "https://speedy-live.pages.dev",
        "https://www.example.test",
    ]


@pytest.mark.parametrize(
    "origins",
    [
        "",
        "*",
        "https://speedy-live.pages.dev,*",
        "http://speedy-live.pages.dev",
        "https://speedy-live.pages.dev/dashboard",
        "https://user:password@example.test",
    ],
)
def test_production_rejects_unsafe_origins(origins):
    with pytest.raises(ValidationError):
        Settings(environment="production", allowed_origins=origins)


def test_development_can_use_local_http_origin():
    settings = Settings(
        environment="development",
        allowed_origins="http://localhost:5173",
    )
    assert settings.cors_origins == ["http://localhost:5173"]
