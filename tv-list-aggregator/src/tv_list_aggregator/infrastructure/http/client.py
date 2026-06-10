"""弹性 HTTP 客户端：限流 + 熔断 + 重试 + 错误归一化。"""
from __future__ import annotations

import time

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ...core.exceptions import (
    PermanentError,
    RateLimitError,
    SourceAuthError,
    SourceUnavailableError,
)
from ...domain.ports.fetcher import Fetcher, FetchResult
from ..resilience.circuit_breaker import AsyncCircuitBreaker
from ..resilience.rate_limiter import TokenBucket


class ResilientHTTPFetcher(Fetcher):
    """综合限流/熔断/重试的 HTTP Fetcher 实现。"""

    def __init__(self, rate_per_minute: int = 60, timeout: float = 30.0) -> None:
        self._client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "TVListAggregator/0.1 (+https://example.com)"},
        )
        self._bucket = TokenBucket(rate_per_minute)
        self._breaker = AsyncCircuitBreaker(name="http-fetcher", fail_max=5, reset_timeout=30.0)

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=0.5, max=8),
        retry=retry_if_exception_type((SourceUnavailableError, RateLimitError, httpx.TransportError)),
    )
    async def fetch(
        self, url: str, *, headers: dict[str, str] | None = None, timeout: float = 30.0
    ) -> FetchResult:
        await self._bucket.acquire()
        start = time.monotonic()
        try:
            resp = await self._breaker.call(
                self._client.get, url, headers=headers, timeout=timeout
            )
        except httpx.TransportError as e:
            raise SourceUnavailableError(str(e)) from e
        elapsed = int((time.monotonic() - start) * 1000)

        if resp.status_code == 429:
            raise RateLimitError(f"rate limited: {url}")
        if resp.status_code in (401, 403):
            raise SourceAuthError(f"http {resp.status_code} {url}")
        if resp.status_code >= 500:
            raise SourceUnavailableError(f"5xx {resp.status_code} {url}")
        if resp.status_code >= 400:
            raise PermanentError(f"http {resp.status_code} {url}")

        return FetchResult(
            url=url,
            status_code=resp.status_code,
            body=resp.content,
            headers=dict(resp.headers),
            elapsed_ms=elapsed,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
