from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import Field
from typing import Annotated

from app.config import get_settings
from app.motion_processing import diagnose_motion_sequence
from app.schemas import MotionFrame

settings = get_settings()
app = FastAPI(
    title=settings.service_name,
    version="0.2.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.environment != "production" else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
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

@app.post("/motion/diagnostics", tags=["motion"])
async def motion_diagnostics(
    frames: Annotated[list[MotionFrame], Field(max_length=3000)],
) -> dict[str, int | float]:
    """Validate a bounded motion batch and report timing/landmark coverage.

    Samples are analyzed as received. No smoothing, interpolation, or artificial
    delay is applied. This endpoint does not generate animation.
    """
    try:
        result = diagnose_motion_sequence(frames)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "sample_count": result.sample_count,
        "duration_ms": result.duration_ms,
        "median_interval_ms": result.median_interval_ms,
        "estimated_fps": result.estimated_fps,
        "max_gap_ms": result.max_gap_ms,
        "body_point_count": result.body_point_count,
        "left_hand_point_count": result.left_hand_point_count,
        "right_hand_point_count": result.right_hand_point_count,
        "face_sample_count": result.face_sample_count,
    }
