"""共享测试配置与夹具。"""
from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """每个测试都用独立的临时 SQLite，避免 lru_cache 跨测试泄漏。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    url = f"sqlite+aiosqlite:///{path}"
    monkeypatch.setenv("TV_LIST_DATABASE_URL", url)
    monkeypatch.setenv("TV_LIST_APP_ENV", "development")
    monkeypatch.setenv("TV_LIST_SECRET_KEY", "test-secret")  # noqa: S105
    monkeypatch.setenv("TV_LIST_BOOTSTRAP_SCHEMA", "1")
    from tv_list_aggregator.core.settings import reset_settings_cache
    from tv_list_aggregator.interfaces.api.deps import reset_deps

    reset_settings_cache()
    reset_deps()
    yield
    # 清理
    import contextlib

    with contextlib.suppress(FileNotFoundError):
        os.unlink(path)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture
async def event_loop() -> AsyncIterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def bootstrapped_app():
    """创建一个已 bootstrap schema 的 FastAPI app（绕过 lifespan 限制）。"""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from tv_list_aggregator.infrastructure.persistence.models import Base
    from tv_list_aggregator.interfaces.api.app import create_app

    s_url = os.environ["TV_LIST_DATABASE_URL"]
    engine = create_async_engine(s_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    app = create_app()
    # 手动注入 lifespan 应设置的 state
    app.state.session_factory = factory
    app.state.engine = engine
    app.state.registry = getattr(app.state, "registry", None)
    app.state.agg = getattr(app.state, "agg", None)

    yield app, engine, factory
    await engine.dispose()
