"""Auth router：POST /api/v1/auth/token 签发 JWT。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.settings import get_settings
from ....domain.services.auth_service import AuthService
from ....infrastructure.persistence.user_repository_impl import (
    SQLAlchemyUserRepository,
)
from ..deps import get_session
from ..security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


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
