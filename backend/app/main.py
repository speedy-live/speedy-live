from contextlib import asynccontextmanager
import logging
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import Field

from app.auth import Principal, require_admin, require_customer
from app.config import get_settings
from app.engine import AnimationEngineUnavailable, EngineRegistry
from app.engine_contract import EngineQualificationError
from app.engine_loader import load_local_engine
from app.motion_processing import diagnose_motion_sequence
from app.schemas import MotionFrame

logger = logging.getLogger(__name__)
settings = get_settings()
engine_registry = EngineRegistry()
backend_root = Path(__file__).resolve().parents[1]
local_engine_root = backend_root / "local_engines"


def customer_animation_is_enabled() -> bool:
    """Require runtime health plus an explicit, auditable customer release approval."""
    return engine_registry.operational and settings.customer_release_approved


@asynccontextmanager
async def lifespan(_: FastAPI):
    adapter_path = settings.animation_engine_adapter_path.strip()
    artifact_path = settings.animation_model_manifest_path.strip()
    if settings.animation_engine != "unconfigured" and adapter_path and artifact_path:
        try:
            load_local_engine(engine_registry, Path(adapter_path), Path(artifact_path),
                              allowed_root=local_engine_root)
            if not await engine_registry.check_runtime():
                logger.error("Local animation engine failed runtime qualification: %s",
                             engine_registry.status().get("runtime_error"))
                engine_registry.clear()
        except Exception as exc:
            logger.exception("Local animation engine startup failed; service remains unready: %s", exc)
            engine_registry.clear()
    else:
        logger.info("No local animation engine configured; photo animation remains unavailable.")
    if engine_registry.operational and not settings.customer_release_approved:
        logger.warning("Local engine passed runtime checks but customer release is disabled: "
                       "an explicit approval flag and approval ID are required.")
    try:
        yield
    finally:
        engine_registry.clear()


app = FastAPI(
    title=settings.service_name, version="0.6.0", lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.environment != "production" else None,
)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
    allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(self), geolocation=()"
    response.headers["Cross-Origin-Resource-Policy"] = "same-site"
    if settings.environment.lower() == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/health", tags=["operations"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "speedy-live-ai"}


@app.get("/ready", tags=["operations"])
async def readiness() -> dict[str, object]:
    engine = engine_registry.status()
    customer_enabled = customer_animation_is_enabled()
    return {
        "status": "ready" if customer_enabled else "not_ready",
        "service_alive": True,
        "animation_engine_configured": bool(engine["configured"]),
        "runtime_health_check_passed": bool(engine["runtime_healthy"]),
        "customer_release_approved": settings.customer_release_approved,
        "customer_animation_enabled": customer_enabled,
        "message": ("The local animation engine is approved for customer use."
                    if customer_enabled else
                    "The service is alive, but customer animation is disabled until runtime checks "
                    "and explicit release approval both pass."),
    }


@app.post("/motion/diagnostics", tags=["motion"])
async def motion_diagnostics(
    frames: Annotated[list[MotionFrame], Field(max_length=3000)],
) -> dict[str, int | float]:
    try:
        result = diagnose_motion_sequence(frames)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "sample_count": result.sample_count, "duration_ms": result.duration_ms,
        "median_interval_ms": result.median_interval_ms, "estimated_fps": result.estimated_fps,
        "max_gap_ms": result.max_gap_ms, "body_point_count": result.body_point_count,
        "left_hand_point_count": result.left_hand_point_count,
        "right_hand_point_count": result.right_hand_point_count,
        "face_sample_count": result.face_sample_count,
    }


@app.get("/customer/me", tags=["customer"])
async def customer_me(principal: Annotated[Principal, Depends(require_customer)]) -> dict[str, str]:
    return {"user_id": principal.user_id, "role": "customer"}


@app.get("/admin/security/overview", tags=["admin"])
async def admin_security_overview(
    principal: Annotated[Principal, Depends(require_admin)],
) -> dict[str, str]:
    return {"admin_user_id": principal.user_id, "access": "administrator"}


@app.get("/engine/status", tags=["engine"])
async def engine_status(
    _: Annotated[Principal, Depends(require_admin)],
) -> dict[str, object]:
    status = engine_registry.status()
    status["customer_release_approved"] = settings.customer_release_approved
    status["customer_animation_enabled"] = customer_animation_is_enabled()
    if status["operational"] and not settings.customer_release_approved:
        status["message"] = (
            "Runtime checks passed, but customer use remains disabled pending explicit release approval."
        )
    return status


@app.get("/engine/capabilities/{mode}", tags=["engine"])
async def engine_capabilities(
    mode: str, _: Annotated[Principal, Depends(require_customer)],
) -> dict[str, object]:
    if mode not in {"portrait", "full_body"}:
        raise HTTPException(status_code=422, detail="Mode must be portrait or full_body.")
    if not customer_animation_is_enabled():
        raise HTTPException(
            status_code=503,
            detail="Customer animation is disabled until runtime qualification and explicit release approval pass.",
        )
    try:
        engine = engine_registry.get(mode, live=(mode == "portrait"))
    except AnimationEngineUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EngineQualificationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    engine_status = engine_registry.status()
    return {
        "available": True, "engine": engine.name, "version": engine.version, "mode": mode,
        "supports_audio_driven_portrait": bool(
            engine_status.get("supports_audio_driven_portrait", False)
        ),
    }
