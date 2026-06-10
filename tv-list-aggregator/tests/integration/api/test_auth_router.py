"""Auth router 集成测试：/api/v1/auth/token 登录流程。"""
from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.fixture
async def temp_db_engine() -> AsyncIterator:
    """临时文件 SQLite 数据库（多 session 可共享）。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    url = f"sqlite+aiosqlite:///{path}"
    engine = create_async_engine(url)
    from tv_list_aggregator.infrastructure.persistence.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine, url
    await engine.dispose()
    with contextlib.suppress(FileNotFoundError):
        os.unlink(path)


@pytest.mark.asyncio
async def test_login_success(temp_db_engine) -> None:
    engine, db_url = temp_db_engine
    os.environ["TV_LIST_DATABASE_URL"] = db_url
    from tv_list_aggregator.core.settings import reset_settings_cache

    reset_settings_cache()

    from tv_list_aggregator.domain.services.auth_service import AuthService
    from tv_list_aggregator.infrastructure.persistence.user_repository_impl import (
        SQLAlchemyUserRepository,
    )

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        svc = AuthService(SQLAlchemyUserRepository(session))
        await svc.create_user("alice", "s3cret", "admin")
        await session.commit()

    from tv_list_aggregator.interfaces.api.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/api/v1/auth/token",
            data={"username": "alice", "password": "s3cret"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["token_type"] == "bearer"  # noqa: S105
        assert "access_token" in body


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(temp_db_engine) -> None:
    engine, db_url = temp_db_engine
    os.environ["TV_LIST_DATABASE_URL"] = db_url
    from tv_list_aggregator.core.settings import reset_settings_cache

    reset_settings_cache()

    from tv_list_aggregator.interfaces.api.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/api/v1/auth/token",
            data={"username": "nobody", "password": "wrong"},
        )
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_invalid_request_body_returns_422() -> None:
    from tv_list_aggregator.interfaces.api.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/v1/auth/token", json={"username": "x"})
        assert r.status_code == 422
