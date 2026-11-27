
"""Signed access token verification and customer/admin authorization."""
from __future__ import annotations
import base64, hashlib, hmac, json, time
from dataclasses import dataclass
from typing import Annotated, Literal
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.account_store import AccountStore
from app.config import get_settings

Role=Literal["customer","admin"]
_bearer=HTTPBearer(auto_error=False)

@dataclass(frozen=True)
class Principal:
    user_id: str
    role: Role
    email: str = ""

def _decode(value: str) -> bytes:
    if not value or len(value)>8192: raise ValueError("Invalid token segment.")
    return base64.urlsafe_b64decode(value+"="*(-len(value)%4))

def verify_access_token(token: str, *, signing_key: str, issuer: str, audience: str,
                        now: int|None=None) -> Principal:
    if len(signing_key.encode())<32: raise ValueError("Authentication signing key is not configured securely.")
    parts=token.split(".")
    if len(parts)!=3: raise ValueError("Malformed token.")
    header=json.loads(_decode(parts[0])); claims=json.loads(_decode(parts[1]))
    if not isinstance(header,dict) or header.get("alg")!="HS256" or header.get("typ")!="JWT":
        raise ValueError("Unsupported token algorithm.")
    signed=f"{parts[0]}.{parts[1]}".encode("ascii")
    expected=hmac.new(signing_key.encode(),signed,hashlib.sha256).digest()
    if not hmac.compare_digest(expected,_decode(parts[2])): raise ValueError("Invalid signature.")
    if not isinstance(claims,dict): raise ValueError("Invalid claims.")
    current=int(time.time()) if now is None else now
    sub,role,issued,expires=claims.get("sub"),claims.get("role"),claims.get("iat"),claims.get("exp")
    aud=claims.get("aud"); aud_ok=aud in audience if isinstance(aud,list) else aud==audience
    email=claims.get("email","")
    if (not isinstance(sub,str) or not sub.strip() or len(sub)>200
        or role not in {"customer","admin"} or claims.get("iss")!=issuer or not aud_ok
        or not isinstance(issued,int) or not isinstance(expires,int) or issued>current+30
        or expires<=current or expires<=issued or expires-issued>3600
        or not isinstance(email,str) or len(email)>254):
        raise ValueError("Invalid or expired claims.")
    return Principal(user_id=sub,role=role,email=email)

def issue_access_token(*, user_id: str, email: str, role: Role, signing_key: str,
                       issuer: str, audience: str, lifetime_seconds: int=900) -> str:
    if len(signing_key.encode())<32: raise ValueError("Authentication signing key is not configured securely.")
    if not 60<=lifetime_seconds<=3600: raise ValueError("Invalid token lifetime.")
    now=int(time.time())
    def enc(obj):
        return base64.urlsafe_b64encode(json.dumps(obj,separators=(",",":"),sort_keys=True).encode()).rstrip(b"=").decode()
    first=enc({"alg":"HS256","typ":"JWT"})
    second=enc({"sub":user_id,"email":email,"role":role,"iss":issuer,"aud":audience,"iat":now,"exp":now+lifetime_seconds})
    signed=f"{first}.{second}".encode("ascii")
    sig=base64.urlsafe_b64encode(hmac.new(signing_key.encode(),signed,hashlib.sha256).digest()).rstrip(b"=").decode()
    return f"{first}.{second}.{sig}"

async def get_current_principal(credentials: Annotated[HTTPAuthorizationCredentials|None,Depends(_bearer)]) -> Principal:
    if credentials is None or credentials.scheme.lower()!="bearer":
        raise HTTPException(status_code=401,detail="A valid sign-in is required.",headers={"WWW-Authenticate":"Bearer"})
    settings=get_settings()
    try:
        principal=verify_access_token(credentials.credentials,signing_key=settings.auth_signing_key,
            issuer=settings.auth_token_issuer,audience=settings.auth_token_audience)
        if not AccountStore(settings.auth_database_path).identity_is_active(user_id=principal.user_id,role=principal.role):
            raise ValueError("Account is inactive or its role changed.")
        return principal
    except (ValueError,TypeError,json.JSONDecodeError,UnicodeDecodeError) as exc:
        raise HTTPException(status_code=401,detail="Invalid or expired sign-in.",headers={"WWW-Authenticate":"Bearer"}) from exc

async def require_customer(principal: Annotated[Principal,Depends(get_current_principal)]) -> Principal:
    if principal.role!="customer": raise HTTPException(status_code=403,detail="Customer access only.")
    return principal

async def require_admin(principal: Annotated[Principal,Depends(get_current_principal)]) -> Principal:
    if principal.role!="admin": raise HTTPException(status_code=403,detail="Administrator access only.")
    return principal
