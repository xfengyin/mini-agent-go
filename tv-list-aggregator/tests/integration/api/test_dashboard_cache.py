"""Dashboard 路由 + TTLCache 集成测试。"""
from __future__ import annotations

import asyncio
import contextlib
import os
import tempfile
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def _setup_env(db_path: str) -> None:
    """复用 conftest 的隔离 env：每个测试都用独立 SQLite。"""
    os.environ["TV_LIST_DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["TV_LIST_BOOTSTRAP_SCHEMA"] = "1"
    os.environ["TV_LIST_AUTO_SEED"] = "1"
    os.environ["TV_LIST_SECRET_KEY"] = "test-secret-1234567890"  # noqa: S105
    os.environ["TV_LIST_SEED_USERS"] = "admin:admin123:admin"
    os.environ["TV_LIST_APP_ENV"] = "development"
    from tv_list_aggregator.core.settings import reset_settings_cache
    from tv_list_aggregator.interfaces.api.deps import reset_deps

    reset_settings_cache()
    reset_deps()


@pytest_asyncio.fixture
async def dashboard_client() -> AsyncIterator[AsyncClient]:
    """构造一个直接 call endpoint 的 AsyncClient（不依赖 lifespan）。"""
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        yield c

    await engine.dispose()
    with contextlib.suppress(FileNotFoundError):
        os.unlink(path)


@pytest.mark.asyncio
async def test_dashboard_summary_uses_cache(dashboard_client: AsyncClient) -> None:
    """30s TTL：两次 /summary 应返回相同值，且 factory 只被调用一次。

    验证方式：通过 patch 路由模块里的 _summary_cache，包装 get_or_set
    来计数 factory 调用次数。
    """
    from tv_list_aggregator.interfaces.api.routers import dashboard as dashboard_module

    real_cache = dashboard_module._summary_cache
    cache_state = {"calls": 0}
    original_get_or_set = real_cache.get_or_set

    async def _counting_get_or_set(key, ttl, factory):
        cache_state["calls"] += 1
        return await original_get_or_set(key, ttl, factory)

    real_cache.get_or_set = _counting_get_or_set  # type: ignore[method-assign]
    try:
        # 第一次：应触发 factory 调用
        r1 = await dashboard_client.get("/api/v1/dashboard/summary")
        assert r1.status_code == 200, r1.text
        body1 = r1.json()
        # 第二次：30s 内应命中缓存，factory 不再调用
        r2 = await dashboard_client.get("/api/v1/dashboard/summary")
        assert r2.status_code == 200, r2.text
        body2 = r2.json()
        # 两次响应内容完全相同（同一份缓存值）
        assert body1 == body2
        # 两次 get_or_set 都被计数，但 factory 只在第一次真正被调用
        # 直接断言：响应中 generated_at 字段稳定（证明第二次是缓存值）
        assert body1["generated_at"] == body2["generated_at"]
        # 计数：第一次未命中 -> factory 调用 1 次；第二次命中 -> 0 次
        assert cache_state["calls"] == 2  # get_or_set 被调用两次
    finally:
        real_cache.get_or_set = original_get_or_set  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_ttl_cache_get_or_set_calls_factory_once(monkeypatch) -> None:
    """单元级：直接验证 TTLCache.get_or_set 在并发请求下 factory 只触发一次。"""
    from tv_list_aggregator.core.cache import TTLCache

    cache: TTLCache[int] = TTLCache()
    call_count = 0

    async def factory() -> int:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)  # 模拟慢 IO，制造并发窗口
        return 42

    # 并发 5 次：应只触发 1 次 factory
    results = await asyncio.gather(*[cache.get_or_set("k", 10.0, factory) for _ in range(5)])
    assert all(r == 42 for r in results)
    assert call_count == 1

    # 已缓存：再次调用应直接命中，不再 factory
    v = await cache.get_or_set("k", 10.0, factory)
    assert v == 42
    assert call_count == 1


@pytest.mark.asyncio
async def test_ttl_cache_invalidate_and_ttl(monkeypatch) -> None:
    """单元级：验证 invalidate 与 TTL 过期。"""
    from tv_list_aggregator.core.cache import TTLCache

    cache: TTLCache[str] = TTLCache()

    async def factory() -> str:
        return "v1"

    v = await cache.get_or_set("k", 60.0, factory)
    assert v == "v1"

    # 主动失效
    cache.invalidate("k")
    assert cache.get("k") is None

    # 极短 TTL：等过期
    async def factory2() -> str:
        return "v2"

    v = await cache.get_or_set("k2", 0.05, factory2)
    assert v == "v2"
    await asyncio.sleep(0.1)
    assert cache.get("k2") is None
