"""Playwright 动态页面抓取器（懒加载 Chromium）。"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from ...domain.ports.fetcher import FetchResult

if TYPE_CHECKING:
    from playwright.async_api import Browser, Playwright


class PlaywrightFetcher:
    """基于 Playwright 的 Fetcher，适合 JS 渲染的动态页面。"""

    def __init__(self, headless: bool = True, timeout_ms: int = 30000) -> None:
        self.headless = headless
        self.timeout_ms = timeout_ms
        self._pw: Playwright | None = None
        self._browser: Browser | None = None

    async def _ensure(self) -> None:
        if self._browser:
            return
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self.headless)

    async def fetch(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        wait_selector: str | None = None,
    ) -> FetchResult:
        await self._ensure()
        assert self._browser is not None
        ctx = await self._browser.new_context(extra_http_headers=headers or {})
        page = await ctx.new_page()
        start = time.monotonic()
        try:
            await page.goto(url, timeout=int(timeout * 1000))
            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=self.timeout_ms)
            body = await page.content()
            return FetchResult(
                url=url,
                status_code=200,
                body=body.encode("utf-8"),
                headers={},
                elapsed_ms=int((time.monotonic() - start) * 1000),
            )
        finally:
            await ctx.close()

    async def aclose(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
