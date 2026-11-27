from contextlib import asynccontextmanager
import logging
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import Principal, issue_access_token, require_admin, require_customer
from app.account_store import AccountStore, AccountStoreError
from app.email_delivery import EmailDeliveryError, send_customer_verification_email
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



class CustomerRegistrationRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=256)


class EmailVerificationRequest(BaseModel):
    token: str = Field(min_length=20, max_length=256)


@app.post("/auth/register", status_code=202, tags=["authentication"])
async def register_customer(request: CustomerRegistrationRequest) -> dict[str, str]:
    """Register a customer; admin accounts can only be provisioned by trusted operators."""
    if not settings.smtp_host or not settings.smtp_from_email:
        raise HTTPException(status_code=503, detail="Customer email verification is not configured.")
    try:
        store = AccountStore(settings.auth_database_path)
        _, token = store.create_customer_registration(
            email=request.email, password=request.password, lifetime_seconds=1800
        )
        base_url = settings.customer_frontend_url.rstrip("/")
        verification_url = f"{base_url}/verify-email?token={quote(token, safe='')}"
        send_customer_verification_email(
            host=settings.smtp_host, port=settings.smtp_port,
            username=settings.smtp_username, password=settings.smtp_password,
            sender=settings.smtp_from_email, recipient=request.email.strip(),
            verification_url=verification_url, use_starttls=settings.smtp_starttls,
        )
        return {"status": "verification_email_sent",
                "message": "Check your email and open the verification link to activate your account."}
    except AccountStoreError as exc:
        if "already exists" in str(exc).lower():
            raise HTTPException(status_code=409, detail="An account with this email already exists.") from exc
        logger.exception("Customer registration storage failure.")
        raise HTTPException(status_code=503, detail="Registration is temporarily unavailable.") from exc
    except (EmailDeliveryError, OSError) as exc:
        logger.exception("Customer verification email delivery failed.")
        raise HTTPException(status_code=503, detail="Verification email could not be sent. Please try again later.") from exc


class VerificationResendRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)


@app.post("/auth/resend-verification", status_code=202, tags=["authentication"])
async def resend_customer_verification(request: VerificationResendRequest) -> dict[str, str]:
    """Resend a customer verification link without revealing whether an email exists."""
    if not settings.smtp_host or not settings.smtp_from_email:
        raise HTTPException(status_code=503, detail="Customer email verification is not configured.")
    try:
        store = AccountStore(settings.auth_database_path)
        token = store.issue_customer_verification_token(email=request.email, lifetime_seconds=1800)
        if token:
            verification_url = (
                f"{settings.customer_frontend_url.rstrip('/')}/verify-email?token={quote(token, safe='')}"
            )
            send_customer_verification_email(
                host=settings.smtp_host, port=settings.smtp_port,
                username=settings.smtp_username, password=settings.smtp_password,
                sender=settings.smtp_from_email, recipient=request.email.strip(),
                verification_url=verification_url, use_starttls=settings.smtp_starttls,
            )
    except (AccountStoreError, EmailDeliveryError, OSError) as exc:
        logger.exception("Customer verification resend failed.")
        raise HTTPException(status_code=503, detail="Verification email could not be sent. Please try again later.") from exc
    return {"status": "accepted",
            "message": "If the account needs verification, a new link will be sent."}


@app.post("/auth/verify-email", tags=["authentication"])
async def verify_customer_email(request: EmailVerificationRequest) -> dict[str, str]:
    try:
        verified = AccountStore(settings.auth_database_path).verify_customer_email(token=request.token)
    except AccountStoreError as exc:
        logger.exception("Customer email verification storage failure.")
        raise HTTPException(status_code=503, detail="Email verification is temporarily unavailable.") from exc
    if not verified:
        raise HTTPException(status_code=400, detail="Verification link is invalid, expired or already used.")
    return {"status": "email_verified", "message": "Your email is verified. You can now sign in."}


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=256)


@app.post("/auth/login", tags=["authentication"])
async def login(request: LoginRequest) -> dict[str, object]:
    """Sign in customers only after email verification; trusted admins are exempt."""
    try:
        account = AccountStore(settings.auth_database_path).authenticate(
            email=request.email, password=request.password
        )
        if account is None:
            raise HTTPException(status_code=401, detail="Email or password is incorrect.")
        token = issue_access_token(
            user_id=account["user_id"], email=account["email"], role=account["role"],
            signing_key=settings.auth_signing_key, issuer=settings.auth_token_issuer,
            audience=settings.auth_token_audience, lifetime_seconds=900,
        )
        return {
            "access_token": token, "token_type": "bearer", "expires_in": 900,
            "user": {"id": account["user_id"], "email": account["email"],
                     "role": account["role"]},
        }
    except AccountStoreError as exc:
        logger.exception("Account database failure during sign-in.")
        raise HTTPException(status_code=503, detail="Sign-in is temporarily unavailable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="Authentication is not configured securely.") from exc


@app.get("/auth/me", tags=["authentication"])
async def auth_me(principal: Annotated[Principal, Depends(require_customer)]):
    return {"id": principal.user_id, "email": principal.email, "role": principal.role}


@app.get("/admin/auth/me", tags=["authentication"])
async def admin_auth_me(principal: Annotated[Principal, Depends(require_admin)]):
    return {"id": principal.user_id, "email": principal.email, "role": principal.role}

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
