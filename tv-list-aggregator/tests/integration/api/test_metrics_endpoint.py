"""Prometheus /metrics 端点集成测试。"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tv_list_aggregator.interfaces.api.app import create_app


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_200_and_text_plain() -> None:
    """GET /metrics 返回 200，content-type 为 text/plain。"""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/metrics")
        assert r.status_code == 200
        assert "text/plain" in r.headers["content-type"]


@pytest.mark.asyncio
async def test_metrics_endpoint_contains_http_metric_names() -> None:
    """GET /metrics 输出至少包含 ``http_requests_total`` 等指标名。"""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # 先打一次请求以触发指标初始化（label 第一次 labels() 时才注册）
        await c.get("/healthz")
        r = await c.get("/metrics")
        assert r.status_code == 200
        body = r.text
        # 至少应出现下列 HTTP 指标之一（Prometheus 文本格式前缀）
        expected_substrings = [
            "http_requests_total",
            "http_request_duration_seconds",
            "http_inprogress_requests",
        ]
        assert any(name in body for name in expected_substrings), (
            f"metrics body 缺少预期的 HTTP 指标: {body[:400]}"
        )


@pytest.mark.asyncio
async def test_metrics_increments_counter_after_request() -> None:
    """多次请求后 ``http_requests_total`` 计数应 >= 1。"""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # 触发几次请求
        for _ in range(3):
            await c.get("/healthz")
        r = await c.get("/metrics")
        assert r.status_code == 200
        # 检查 ``http_requests_total{...,path="/healthz",...}`` 行
        body = r.text
        # 至少应有一行 http_requests_total 计数 >= 3
        hit = False
        for line in body.splitlines():
            if line.startswith("http_requests_total{") and "/healthz" in line:
                # 形如: http_requests_total{...,path="/healthz",status="200"} 3.0
                try:
                    value = float(line.rsplit(" ", 1)[-1])
                except ValueError:
                    continue
                if value >= 1:
                    hit = True
                    break
        assert hit, f"未在 /metrics 输出中找到 /healthz 计数: {body[:600]}"
