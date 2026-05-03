from typing import Optional
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import JWT_ALGORITHM, JWT_ISSUER, JWT_SECRET
from errors import forbidden, unauthorized
from schemas import AuthContext


security = HTTPBearer(auto_error=False)


def get_current_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthContext:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise unauthorized()

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
        )
    except jwt.ExpiredSignatureError:
        raise unauthorized("Token has expired")
    except jwt.InvalidTokenError:
        raise unauthorized("Invalid token")

    try:
        tenant_id = payload.get("tenant_id")
        auth = AuthContext(
            sub=payload["sub"],
            role=payload["role"],
            tenant_id=UUID(tenant_id) if tenant_id else None,
            exp=payload["exp"],
            iss=payload["iss"],
        )
    except Exception:
        raise unauthorized("Invalid token claims")

    if auth.role == "tenant" and auth.tenant_id is None:
        raise unauthorized("Tenant token missing tenant scope")

    return auth


def require_admin(auth: AuthContext) -> AuthContext:
    if auth.role != "admin":
        raise forbidden("Admin access required")
    return auth


def ensure_tenant_access(auth: AuthContext, tenant_id: UUID) -> None:
    if auth.role == "admin":
        return
    if auth.role == "tenant" and auth.tenant_id == tenant_id:
        return
    raise forbidden("Tenant scope does not allow access to this tenant")
