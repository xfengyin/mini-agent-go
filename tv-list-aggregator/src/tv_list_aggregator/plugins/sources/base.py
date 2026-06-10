"""源适配器协议（SPI 抽象）。"""
from __future__ import annotations

from typing import Protocol

from ...domain.models.program import TVProgram
from ...domain.models.source import TVListSource
from ...domain.ports.fetcher import FetchResult


class SourceAdapter(Protocol):
    """源适配器协议：fetch + parse。"""

    type: str

    async def fetch(self, source: TVListSource) -> FetchResult: ...

    async def parse(self, result: FetchResult, source: TVListSource) -> list[TVProgram]: ...
