"""Server-side identity verification and role-based API dependencies.

Tokens are issued only by a trusted authentication service. This module deliberately
provides no public token-issuing endpoint and never trusts role/user IDs from request bodies.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

Role = Literal["customer", "admin"]
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: Role


def _b64url_decode(value: str) -> bytes:
    if not value or len(value) > 8192:
        raise ValueError("Invalid token segment.")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def verify_access_token(token: str, *, signing_key: str, issuer: str, audience: str,
                        now: int | None = None) -> Principal:
    """Verify a compact HS256 access token with strict claims and expiry checks."""
    if len(signing_key.encode("utf-8")) < 32:
        raise ValueError("Authentication signing key is not configured securely.")
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed access token.")
    header = json.loads(_b64url_decode(parts[0]))
    claims = json.loads(_b64url_decode(parts[1]))
    if not isinstance(header, dict) or header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise ValueError("Unsupported token algorithm.")
    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    expected = hmac.new(signing_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(parts[2])):
        raise ValueError("Invalid token signature.")
    if not isinstance(claims, dict):
        raise ValueError("Invalid token claims.")
    current = int(time.time()) if now is None else now
    subject, role = claims.get("sub"), claims.get("role")
    issued, expires = claims.get("iat"), claims.get("exp")
    token_audience = claims.get("aud")
    audience_ok = audience in token_audience if isinstance(token_audience, list) else token_audience == audience
    if (
        not isinstance(subject, str) or not subject.strip() or len(subject) > 200
        or role not in {"customer", "admin"}
        or claims.get("iss") != issuer or not audience_ok
        or not isinstance(issued, int) or not isinstance(expires, int)
        or issued > current + 30 or expires <= current or expires <= issued
        or expires - issued > 3600
    ):
        raise ValueError("Invalid or expired token claims.")
    return Principal(user_id=subject, role=role)


async def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="A valid sign-in is required.",
                            headers={"WWW-Authenticate": "Bearer"})
    settings = get_settings()
    try:
        return verify_access_token(
            credentials.credentials,
            signing_key=settings.auth_signing_key,
            issuer=settings.auth_token_issuer,
            audience=settings.auth_token_audience,
        )
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired sign-in.",
                            headers={"WWW-Authenticate": "Bearer"}) from exc


async def require_customer(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> Principal:
    if principal.role != "customer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Customer access only.")
    return principal


async def require_admin(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> Principal:
    if principal.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Administrator access only.")
    return principal
