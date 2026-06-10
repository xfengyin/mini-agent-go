"""Sources router 集成测试：CRUD + enable/disable。"""
from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.fixture
async def shared_db() -> AsyncIterator[str]:
    """临时文件 SQLite 数据库（多 session 可共享）。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    url = f"sqlite+aiosqlite:///{path}"
    engine = create_async_engine(url)
    from tv_list_aggregator.infrastructure.persistence.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield url
    await engine.dispose()
    with contextlib.suppress(FileNotFoundError):
        os.unlink(path)


def _build_app(shared_db: str):
    """装配测试用 FastAPI app：注入 lifespan 风格的 session_factory，避免跨测试污染模块级缓存。"""
    os.environ["TV_LIST_DATABASE_URL"] = shared_db
    from tv_list_aggregator.core.settings import reset_settings_cache

    reset_settings_cache()
    # 关键：清空 deps 模块级 engine/session_factory 缓存，
    # 防止上一次测试关闭 temp 文件后，本次请求仍写到旧 db。
    from tv_list_aggregator.interfaces.api.deps import reset_deps

    reset_deps()

    from tv_list_aggregator.interfaces.api.app import create_app

    app = create_app()
    # 手动注入 session_factory 与 engine，等价于 lifespan 的前半段；
    # ASGITransport 默认不触发 lifespan。
    from tv_list_aggregator.infrastructure.persistence.sqlalchemy_base import (
        make_engine,
        make_session_factory,
    )

    engine = make_engine(shared_db)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    return app


@pytest.mark.asyncio
async def test_create_and_list_source(shared_db: str) -> None:
    from tv_list_aggregator.interfaces.api.security import create_access_token

    app = _build_app(shared_db)
    token = create_access_token("u1", "admin", ttl_min=10)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/api/v1/sources",
            json={
                "id": "src1",
                "name": "demo",
                "type": "http_json",
                "url": "https://example.com",
                "cron": "*/5 * * * *",
                "parser": "json",
            },
            headers=headers,
        )
        assert r.status_code == 201, r.text
        r = await c.get("/api/v1/sources", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert any(s["id"] == "src1" for s in body)


@pytest.mark.asyncio
async def test_create_source_requires_admin_role(shared_db: str) -> None:
    from tv_list_aggregator.interfaces.api.security import create_access_token

    app = _build_app(shared_db)
    user_token = create_access_token("u2", "user", ttl_min=10)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/api/v1/sources",
            json={
                "id": "x",
                "name": "x",
                "type": "http_json",
                "url": "u",
                "cron": "* * * * *",
                "parser": "json",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_source_not_found(shared_db: str) -> None:
    from tv_list_aggregator.interfaces.api.security import create_access_token

    app = _build_app(shared_db)
    token = create_access_token("u3", "user", ttl_min=10)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get(
            "/api/v1/sources/missing", headers={"Authorization": f"Bearer {token}"}
        )
        assert r.status_code == 404
