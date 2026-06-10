"""Admin router 集成测试：/api/v1/admin/plugins + /api/v1/admin/crawl/{id}。"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tv_list_aggregator.interfaces.api.app import create_app


@pytest.mark.asyncio
async def test_list_plugins_ok() -> None:
    app = create_app()
    # 注入一个 fake registry
    from tv_list_aggregator.plugins.registry import PluginRegistry

    reg = PluginRegistry()
    reg.register_source("http_json", lambda: None)
    reg.register_parser("json", object())
    app.state.registry = reg

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/v1/admin/plugins")
        assert r.status_code == 200
        body = r.json()
        assert "http_json" in body["source_types"]
        assert "json" in body["parsers"]


@pytest.mark.asyncio
async def test_list_plugins_no_registry_returns_503() -> None:
    app = create_app()
    if hasattr(app.state, "registry"):
        del app.state.registry
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/v1/admin/plugins")
        assert r.status_code == 503


@pytest.mark.asyncio
async def test_trigger_crawl_source_not_found() -> None:
    app = create_app()
    from unittest.mock import AsyncMock

    from tv_list_aggregator.plugins.registry import PluginRegistry

    app.state.registry = PluginRegistry()
    app.state.source_repo = AsyncMock()
    app.state.source_repo.get = AsyncMock(return_value=None)
    app.state.agg = AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/v1/admin/crawl/missing")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_trigger_crawl_app_not_initialized() -> None:
    app = create_app()
    # 移除所有 app.state 注入
    for k in ("registry", "source_repo", "agg"):
        if hasattr(app.state, k):
            delattr(app.state, k)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/v1/admin/crawl/x")
        assert r.status_code == 503
