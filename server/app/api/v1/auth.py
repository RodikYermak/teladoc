from fastapi import APIRouter

from app.core.errors import unauthorized
from app.models.schemas import LoginRequest, LoginResponse
from app.services.auth_service import authenticate_user, create_access_token


router = APIRouter()


@router.post("/v1/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    user = authenticate_user(payload.identifier, payload.password)
    if not user:
        raise unauthorized("Invalid username/email or password")

    access_token, expires_at = create_access_token(user)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_at=expires_at,
        user={
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "display_name": user["display_name"],
            "tenant_id": user["tenant_id"],
        },
    )
