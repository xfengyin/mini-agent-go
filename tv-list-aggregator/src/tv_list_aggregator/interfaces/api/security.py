"""JWT 鉴权与角色控制。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from ...core.settings import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=True)

ROLE_ADMIN = "admin"
ROLE_USER = "user"


def create_access_token(sub: str, role: str = ROLE_USER, ttl_min: int | None = None) -> str:
    """签发 JWT。"""
    s = get_settings()
    ttl = ttl_min or s.access_token_ttl_min
    payload = {
        "sub": sub,
        "role": role,
        "exp": datetime.now(tz=UTC) + timedelta(minutes=ttl),
    }
    return jwt.encode(payload, s.secret_key, algorithm=s.jwt_algorithm)


def require_role(required: str):
    """依赖注入：要求 JWT 中具有指定角色（admin 始终通过）。"""

    def _checker(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
        s = get_settings()
        try:
            payload = jwt.decode(token, s.secret_key, algorithms=[s.jwt_algorithm])
        except JWTError as e:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from e
        if required not in (payload.get("role"), ROLE_ADMIN):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient role")
        return payload

    return _checker
