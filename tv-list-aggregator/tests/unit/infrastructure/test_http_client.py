"""弹性 HTTP 客户端测试。"""
from __future__ import annotations

import httpx
import pytest
import respx

from tv_list_aggregator.core.exceptions import RateLimitError
from tv_list_aggregator.infrastructure.http.client import ResilientHTTPFetcher


@pytest.mark.asyncio
async def test_fetch_retries_on_5xx_then_succeeds() -> None:
    fetcher = ResilientHTTPFetcher(rate_per_minute=10000)
    with respx.mock(base_url="https://x") as mock:
        route = mock.get("/p").mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(200, content=b"ok"),
            ]
        )
        result = await fetcher.fetch("https://x/p")
        assert result.status_code == 200
        assert route.call_count == 2
    await fetcher.aclose()


@pytest.mark.asyncio
async def test_fetch_429_raises_rate_limit() -> None:
    fetcher = ResilientHTTPFetcher(rate_per_minute=10000)
    with respx.mock(base_url="https://x") as mock:
        mock.get("/p").mock(return_value=httpx.Response(429))
        with pytest.raises(RateLimitError):
            await fetcher.fetch("https://x/p")
    await fetcher.aclose()


@pytest.mark.asyncio
async def test_fetch_404_is_permanent() -> None:
    fetcher = ResilientHTTPFetcher(rate_per_minute=10000)
    with respx.mock(base_url="https://x") as mock:
        mock.get("/p").mock(return_value=httpx.Response(404))
        from tv_list_aggregator.core.exceptions import PermanentError

        with pytest.raises(PermanentError):
            await fetcher.fetch("https://x/p")
    await fetcher.aclose()
