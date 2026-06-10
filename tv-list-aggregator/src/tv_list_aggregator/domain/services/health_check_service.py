"""健康检查服务：检测源是否可用并返回延迟。"""
from __future__ import annotations

import time
from datetime import UTC, datetime

from ...core.exceptions import SourceUnavailableError
from ..models.health import SourceHealth
from ..models.source import TVListSource
from ..ports.fetcher import Fetcher


class HealthCheckService:
    """对单个源执行 HEAD/GET 健康检查。"""

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    async def check(self, source: TVListSource) -> SourceHealth:
        if not source.url:
            return SourceHealth(
                source_id=source.id,
                is_alive=False,
                latency_ms=None,
                checked_at=datetime.now(tz=UTC),
                message="no url configured",
            )
        start = time.monotonic()
        try:
            await self.fetcher.fetch(str(source.url), headers=source.headers or None, timeout=10.0)
            return SourceHealth(
                source_id=source.id,
                is_alive=True,
                latency_ms=int((time.monotonic() - start) * 1000),
                checked_at=datetime.now(tz=UTC),
            )
        except SourceUnavailableError as e:
            return SourceHealth(
                source_id=source.id,
                is_alive=False,
                latency_ms=None,
                checked_at=datetime.now(tz=UTC),
                message=str(e)[:500],
            )
        except Exception as e:  # noqa: BLE001
            return SourceHealth(
                source_id=source.id,
                is_alive=False,
                latency_ms=None,
                checked_at=datetime.now(tz=UTC),
                message=f"unexpected: {e}"[:500],
            )
