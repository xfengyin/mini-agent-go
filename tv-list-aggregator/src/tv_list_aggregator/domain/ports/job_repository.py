"""任务仓储接口。"""
from __future__ import annotations

from typing import Protocol

from ..models.crawl_job import CrawlJob, JobStatus


class JobRepository(Protocol):
    """任务仓储协议。"""

    async def add(self, job: CrawlJob) -> None: ...
    async def update(self, job: CrawlJob) -> None: ...
    async def list(
        self,
        *,
        source_id: str | None = None,
        status: JobStatus | None = None,
        limit: int = 50,
    ) -> list[CrawlJob]: ...
