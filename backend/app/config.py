from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "SPEEDY LIVE AI API"
    environment: str = "development"
    allowed_origins: str = "http://localhost:5173"
    animation_engine: str = "unconfigured"
    animation_engine_adapter_path: str = ""
    animation_model_manifest_path: str = ""
    # Customer-facing use is a separate, explicit release decision. Runtime health
    # alone must never expose an unreviewed model to customers.
    animation_engine_customer_release_approved: bool = False
    animation_engine_release_approval_id: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_origins(self):
        if self.environment.lower() != "production":
            return self

        origins = self.cors_origins
        if not origins or "*" in origins:
            raise ValueError(
                "Production ALLOWED_ORIGINS must contain explicit HTTPS website origins; "
                "wildcards and empty values are not allowed."
            )

        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme != "https"
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
            ):
                raise ValueError(
                    "Every production ALLOWED_ORIGINS entry must be an HTTPS origin "
                    "without a path, query, credentials, or fragment."
                )
        return self

    @property
    def customer_release_approved(self) -> bool:
        return bool(
            self.animation_engine_customer_release_approved
            and self.animation_engine_release_approval_id.strip()
        )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
