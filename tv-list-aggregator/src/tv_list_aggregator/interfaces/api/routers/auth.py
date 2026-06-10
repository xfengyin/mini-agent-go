"""Auth router：POST /api/v1/auth/token 签发 JWT；POST /api/v1/auth/refresh 续签。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.settings import get_settings
from ....domain.services.auth_service import AuthService
from ....infrastructure.persistence.user_repository_impl import (
    SQLAlchemyUserRepository,
)
from ..deps import get_session
from ..schemas.auth import RefreshOut
from ..security import create_access_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])


# /auth/refresh 单独使用 bearer 鉴权：与 oauth2_scheme 复用同样 tokenUrl 即可
# auto_error=False 让我们自己返回 401，避免覆盖通用 OAuth2PasswordBearer 错误
_refresh_bearer = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


@router.post("/token")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """OAuth2 兼容 token endpoint。

    成功返回 {"access_token": ..., "token_type": "bearer"}
    失败 401。
    """
    svc = AuthService(SQLAlchemyUserRepository(session))
    user = await svc.authenticate(form.username, form.password)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    ttl = get_settings().access_token_ttl_min
    token = create_access_token(sub=user.id, role=user.role, ttl_min=ttl)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/refresh", response_model=RefreshOut)
async def refresh_token(
    token: str | None = Depends(_refresh_bearer),
) -> RefreshOut:
    """用尚未过期的 access token 续签一个新 token。

    设计：
    - 校验当前 token 签名 + 过期时间（decode_token 内部 jose 校验）；
    - 不重新走 authenticate（避免要求用户再传密码），符合 RFC 6750 续签语义；
    - 撤销检查：当前项目 token 撤销表尚未实现，预留 hook（见下方注释），
      如未来引入黑名单（jti / version 字段），应在此处增量校验并返回 401。
    """
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if payload is None:
        # 签名错 / 过期 / 格式非法 统一视为 401
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sub = payload.get("sub")
    role = payload.get("role") or "user"
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token payload")

    # TODO 撤销检查：未来若引入 token_version / jti 黑名单，在此校验失败时返回 401。
    new_token = create_access_token(
        sub=sub, role=str(role), ttl_min=get_settings().access_token_ttl_min
    )
    return RefreshOut(access_token=new_token, token_type="bearer")  # noqa: S106
