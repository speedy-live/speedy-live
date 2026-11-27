from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.service_name,
    version="0.1.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.environment != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health", tags=["operations"])
async def health() -> dict[str, str]:
    """Confirms that the API process is responding."""
    return {"status": "ok", "service": "speedy-live-ai"}


@app.get("/ready", tags=["operations"])
async def readiness() -> dict[str, str | bool]:
    """Reports engine configuration without pretending inference is available."""
    configured = settings.animation_engine != "unconfigured"
    return {
        "status": "ready" if configured else "not_ready",
        "animation_engine_configured": configured,
        "message": (
            "An animation engine is configured; inference still requires qualification tests."
            if configured
            else "No animation engine is configured. Photo animation is not available."
        ),
    }
