"""Auth router 集成测试：/api/v1/auth/token 登录流程 + /api/v1/auth/refresh 续签。"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def auth_engine() -> AsyncIterator:
    """在 conftest 隔离的临时 SQLite 上 bootstrap schema。"""
    from tv_list_aggregator.infrastructure.persistence.models import Base

    s_url = os.environ["TV_LIST_DATABASE_URL"]
    engine = create_async_engine(s_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_login_success(auth_engine) -> None:
    """正确凭证应返回 bearer token。"""
    from tv_list_aggregator.domain.services.auth_service import AuthService
    from tv_list_aggregator.infrastructure.persistence.user_repository_impl import (
        SQLAlchemyUserRepository,
    )
    from tv_list_aggregator.interfaces.api.app import create_app

    factory = async_sessionmaker(auth_engine, expire_on_commit=False)
    async with factory() as session:
        svc = AuthService(SQLAlchemyUserRepository(session))
        await svc.create_user("alice", "s3cret", "admin")  # noqa: S106
        await session.commit()

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/api/v1/auth/token",
            data={"username": "alice", "password": "s3cret"},  # noqa: S106
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["token_type"] == "bearer"  # noqa: S105
        assert "access_token" in body


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(auth_engine) -> None:
    """错误密码应返回 401。"""
    from tv_list_aggregator.interfaces.api.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/api/v1/auth/token",
            data={"username": "nobody", "password": "wrong"},  # noqa: S106
        )
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_success(auth_engine) -> None:
    """未过期的有效 token 应能续签成新 token。"""
    from datetime import UTC, datetime, timedelta

    from jose import jwt  # type: ignore[import-untyped]

    from tv_list_aggregator.core.settings import get_settings
    from tv_list_aggregator.interfaces.api.app import create_app

    s = get_settings()
    # 手搓一个未过期 token（不通过 /auth/token）
    valid = jwt.encode(
        {
            "sub": "user-1",
            "role": "user",
            "exp": datetime.now(tz=UTC) + timedelta(minutes=10),
        },
        s.secret_key.get_secret_value(),
        algorithm=s.jwt_algorithm,
    )

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {valid}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["token_type"] == "bearer"  # noqa: S105
        assert isinstance(body["access_token"], str)  # noqa: S105
        # 新 token 应能成功解码且 sub 保持一致
        new_payload = jwt.decode(
            body["access_token"],  # noqa: S105
            s.secret_key.get_secret_value(),
            algorithms=[s.jwt_algorithm],
        )
        assert new_payload["sub"] == "user-1"
        assert new_payload["role"] == "user"


@pytest.mark.asyncio
async def test_refresh_token_expired_returns_401(auth_engine) -> None:
    """已过期的 token 应返回 401（不允许续签）。"""
    from datetime import UTC, datetime, timedelta

    from jose import jwt  # type: ignore[import-untyped]

    from tv_list_aggregator.core.settings import get_settings
    from tv_list_aggregator.interfaces.api.app import create_app

    s = get_settings()
    expired = jwt.encode(
        {
            "sub": "user-1",
            "role": "user",
            # 已经过期 1 分钟
            "exp": datetime.now(tz=UTC) - timedelta(minutes=1),
        },
        s.secret_key.get_secret_value(),
        algorithm=s.jwt_algorithm,
    )

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {expired}"},
        )
        assert r.status_code == 401, r.text


@pytest.mark.asyncio
async def test_refresh_token_missing_returns_401(auth_engine) -> None:
    """缺少 Authorization header 应返回 401。"""
    from tv_list_aggregator.interfaces.api.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/v1/auth/refresh")
        assert r.status_code == 401, r.text


@pytest.mark.asyncio
async def test_refresh_token_invalid_signature_returns_401(auth_engine) -> None:
    """签名错误的 token 应返回 401。"""
    from tv_list_aggregator.interfaces.api.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": "Bearer not.a.valid.jwt"},
        )
        assert r.status_code == 401, r.text
