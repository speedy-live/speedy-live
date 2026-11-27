from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "SPEEDY LIVE AI API"
    environment: str = "development"
    allowed_origins: str = "http://localhost:5173"
    animation_engine: str = "unconfigured"
    animation_engine_adapter_path: str = ""
    animation_model_manifest_path: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
