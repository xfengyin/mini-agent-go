"""JWT 鉴权与角色控制。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt  # type: ignore[import-untyped]

from ...core.settings import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=True)

ROLE_ADMIN = "admin"
ROLE_USER = "user"


def create_access_token(sub: str, role: str = ROLE_USER, ttl_min: int | None = None) -> str:
    """签发 JWT。"""
    s = get_settings()
    ttl = ttl_min or s.access_token_ttl_min
    payload: dict[str, Any] = {
        "sub": sub,
        "role": role,
        "exp": datetime.now(tz=UTC) + timedelta(minutes=ttl),
    }
    # SecretStr.get_secret_value() 显式取值
    encoded: str = jwt.encode(  # type: ignore[no-any-return]
        payload, s.secret_key.get_secret_value(), algorithm=s.jwt_algorithm
    )
    return encoded


def decode_token(token: str) -> dict[str, Any] | None:
    """解码并校验 JWT。

    返回 payload（dict）表示 token 有效且未过期；
    任何 JWTError（签名错误、过期、格式非法）都返回 None，
    避免上层依赖耦合到 jose 异常类型。
    """
    s = get_settings()
    try:
        return jwt.decode(  # type: ignore[return-value]
            token, s.secret_key.get_secret_value(), algorithms=[s.jwt_algorithm]
        )
    except JWTError:
        return None


def require_role(required: str):
    """依赖注入：要求 JWT 中具有指定角色（admin 始终通过）。"""

    def _checker(token: Annotated[str, Depends(oauth2_scheme)]) -> dict[str, Any]:
        s = get_settings()
        try:
            payload: dict[str, Any] = jwt.decode(  # type: ignore[assignment]
                token, s.secret_key.get_secret_value(), algorithms=[s.jwt_algorithm]
            )
        except JWTError as e:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from e
        # admin 拥有所有权限；否则只允许 role == required
        user_role = payload.get("role")
        if user_role not in (required, ROLE_ADMIN):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient role")
        return payload

    return _checker
