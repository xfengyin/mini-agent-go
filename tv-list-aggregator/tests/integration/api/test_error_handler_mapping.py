"""ErrorHandlerMiddleware 内置异常映射测试。

覆盖：ValueError -> 400、PermissionError -> 403、KeyError -> 404。
策略：临时往 FastAPI app 注入一个故意抛异常的端点，验证状态码与 problem+json body。
"""
from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def _setup_env(db_path: str) -> None:
    os.environ["TV_LIST_DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["TV_LIST_BOOTSTRAP_SCHEMA"] = "1"
    os.environ["TV_LIST_SECRET_KEY"] = "test-secret-1234567890"  # noqa: S105
    os.environ["TV_LIST_APP_ENV"] = "development"
    from tv_list_aggregator.core.settings import reset_settings_cache
    from tv_list_aggregator.interfaces.api.deps import reset_deps

    reset_settings_cache()
    reset_deps()


@pytest_asyncio.fixture
async def error_app() -> AsyncIterator[AsyncClient]:
    """装配一个带 error-inject 路由的 app 用于测试。"""
    from tv_list_aggregator.infrastructure.persistence.models import Base
    from tv_list_aggregator.interfaces.api.app import create_app

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    _setup_env(path)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    app = create_app()
    app.state.session_factory = factory
    app.state.engine = engine

    # 注入三个故意抛内置异常的端点
    inject = APIRouter()

    @inject.get("/_err/value")
    async def _v() -> None:
        raise ValueError("bad input")

    @inject.get("/_err/permission")
    async def _p() -> None:
        raise PermissionError("not allowed")

    @inject.get("/_err/key")
    async def _k() -> None:
        raise KeyError("missing-resource-id")

    app.include_router(inject)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        yield c

    await engine.dispose()
    with contextlib.suppress(FileNotFoundError):
        os.unlink(path)


@pytest.mark.asyncio
async def test_value_error_maps_to_400(error_app: AsyncClient) -> None:
    """ValueError 应被中间件映射为 400 Bad Request。"""
    r = await error_app.get("/_err/value")
    assert r.status_code == 400
    body = r.json()
    assert body["title"] == "Bad Request"
    assert body["status"] == 400
    assert "bad input" in body["detail"]
    assert body["type"] == "/problems/value-error"


@pytest.mark.asyncio
async def test_permission_error_maps_to_403(error_app: AsyncClient) -> None:
    """PermissionError 应被中间件映射为 403 Forbidden。"""
    r = await error_app.get("/_err/permission")
    assert r.status_code == 403
    body = r.json()
    assert body["title"] == "Forbidden"
    assert body["status"] == 403
    assert "not allowed" in body["detail"]
    assert body["type"] == "/problems/permission-error"


@pytest.mark.asyncio
async def test_key_error_maps_to_404(error_app: AsyncClient) -> None:
    """KeyError 应被中间件映射为 404 Not Found。"""
    r = await error_app.get("/_err/key")
    assert r.status_code == 404
    body = r.json()
    assert body["title"] == "Not Found"
    assert body["status"] == 404
    # detail 不带 Python repr 的引号
    assert "missing-resource-id" in body["detail"]
    assert body["type"] == "/problems/key-error"
