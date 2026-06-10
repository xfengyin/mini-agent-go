"""FastAPI 集成测试。"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_healthz() -> None:
    # 延迟导入避免 lifespan 副作用
    from tv_list_aggregator.interfaces.api.app import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/healthz")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_metrics_endpoint() -> None:
    from tv_list_aggregator.interfaces.api.app import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/metrics")
        assert r.status_code == 200
        assert "text/plain" in r.headers["content-type"]


@pytest.mark.asyncio
async def test_request_id_propagated() -> None:
    from tv_list_aggregator.interfaces.api.app import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/healthz", headers={"x-request-id": "abc-123"})
        assert r.headers.get("x-request-id") == "abc-123"
