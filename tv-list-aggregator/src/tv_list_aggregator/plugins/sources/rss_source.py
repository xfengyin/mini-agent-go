"""RSS 源适配器。"""
from __future__ import annotations

from ...domain.models.program import TVProgram
from ...domain.models.source import TVListSource
from ...domain.ports.fetcher import Fetcher, FetchResult
from ...domain.ports.parser import Parser


class RSSSource:
    """RSS 源适配器（解析复用通用 Parser 链）。"""

    type = "rss"

    def __init__(self, fetcher: Fetcher, parser: Parser) -> None:
        self.fetcher = fetcher
        self.parser = parser

    async def fetch(self, source: TVListSource) -> FetchResult:
        if not source.url:
            raise ValueError(f"source {source.id} has no url")
        return await self.fetcher.fetch(str(source.url), headers=source.headers or None)

    async def parse(self, result: FetchResult, source: TVListSource) -> list[TVProgram]:
        return await self.parser.parse(result.body, hint={"source_id": source.id, "format": "rss"})
