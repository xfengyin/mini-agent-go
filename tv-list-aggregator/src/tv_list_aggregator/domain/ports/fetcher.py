"""Fetcher 端口：抽象 HTTP 抓取能力。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class FetchResult:
    """抓取结果：URL/状态码/二进制 body/响应头/耗时。"""

    url: str
    status_code: int
    body: bytes
    headers: dict[str, str]
    elapsed_ms: int


class Fetcher(Protocol):
    """通用 Fetcher 接口。"""

    async def fetch(
        self, url: str, *, headers: dict[str, str] | None = None, timeout: float = 30.0
    ) -> FetchResult: ...
