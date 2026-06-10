"""HTML 抓取源适配器（Playwright + 解析器链）。"""
from __future__ import annotations

import logging

from ...domain.models.program import TVProgram
from ...domain.models.source import TVListSource
from ...domain.ports.fetcher import FetchResult
from ...domain.ports.parser import Parser
from ...infrastructure.http.playwright_fetcher import PlaywrightFetcher

logger = logging.getLogger(__name__)


class HTMLScrapeSource:
    """动态 HTML 抓取源。"""

    type = "html_scrape"

    def __init__(self, fetcher: PlaywrightFetcher, parsers: list[Parser]) -> None:
        self.fetcher = fetcher
        self.parsers = parsers  # 链式：html -> llm

    async def fetch(self, source: TVListSource) -> FetchResult:
        if not source.url:
            raise ValueError(f"source {source.id} has no url")
        wait_sel_raw: object = source.config.get("wait_selector")
        wait_selector: str | None = wait_sel_raw if isinstance(wait_sel_raw, str) else None
        return await self.fetcher.fetch(
            str(source.url),
            headers=source.headers or None,
            wait_selector=wait_selector,
        )

    async def parse(self, result: FetchResult, source: TVListSource) -> list[TVProgram]:
        for parser in self.parsers:
            try:
                programs = await parser.parse(result.body, hint={"source_id": source.id})
                if programs:
                    return programs
            except Exception:
                logger.exception("html_scrape_source: parser %s failed", getattr(parser, "type", parser))
                continue
        return []
