import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt

from config import JWT_ALGORITHM, JWT_EXPIRES_MINUTES, JWT_ISSUER, JWT_SECRET
from dev_data import FAKE_USERS


def create_access_token(user: dict) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRES_MINUTES)
    payload = {
        "sub": user["username"],
        "role": user["role"],
        "tenant_id": user["tenant_id"],
        "iss": JWT_ISSUER,
        "exp": expires_at,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expires_at


def authenticate_user(identifier: str, password: str) -> Optional[dict]:
    identifier_lower = identifier.strip().lower()
    for user in FAKE_USERS:
        matches_identifier = (
            user["username"].lower() == identifier_lower
            or user["email"].lower() == identifier_lower
        )
        password_matches = secrets.compare_digest(user["password"], password)
        if matches_identifier and password_matches:
            return user
    return None
