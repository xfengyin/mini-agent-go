"""聚合服务：编排 fetch→parse→dedup→save。"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from ...core.logging import get_logger
from ..models.crawl_job import CrawlJob, JobStatus
from ..models.program import TVProgram
from ..models.source import TVListSource
from ..ports.fetcher import Fetcher
from ..ports.job_repository import JobRepository
from ..ports.parser import Parser
from ..ports.program_repository import ProgramRepository
from .dedup_service import DedupService
from .normalization_service import NormalizationService

log = get_logger(__name__)

# 简单类型别名：session 工厂（async_sessionmaker[AsyncSession]）
SessionFactory = Callable[..., Any]


class AggregationService:
    """一次抓取编排：构造 job→fetch→parse→normalize→dedup→upsert→更新 job。

    修复 issue #7：当提供 session_factory 时，所有 program upsert 在同一事务中执行；
    失败时回滚、job 状态标 PARTIAL_FAILURE 且 items_saved 反映实际提交数。
    """

    def __init__(
        self,
        fetcher: Fetcher,
        parser: Parser,
        program_repo: ProgramRepository,
        job_repo: JobRepository,
        dedup: DedupService,
        normalizer: NormalizationService,
        session_factory: SessionFactory | None = None,
    ) -> None:
        self.fetcher = fetcher
        self.parser = parser
        self.program_repo = program_repo
        self.job_repo = job_repo
        self.dedup = dedup
        self.normalizer = normalizer
        self.session_factory = session_factory

    async def run_once(self, source: TVListSource) -> CrawlJob:
        job = CrawlJob(
            id=str(uuid.uuid4()),
            source_id=source.id,
            status=JobStatus.RUNNING,
            started_at=datetime.now(tz=UTC),
        )
        await self.job_repo.add(job)
        saved = 0
        try:
            if not source.url:
                raise ValueError(f"source {source.id} has no url")
            result = await self.fetcher.fetch(str(source.url), headers=source.headers or None)
            programs = await self.parser.parse(result.body, hint={"source_id": source.id})
            programs = [self._apply_norm(p) for p in programs]
            programs = self.dedup.merge(programs)

            if self.session_factory is not None:
                # 单事务路径：成功提交则全部保存，失败则全部回滚
                async with self.session_factory() as session, session.begin():
                    for p in programs:
                        await self.program_repo.upsert(p)
                        saved += 1
            else:
                # 兼容旧调用方：每条独立 flush
                for p in programs:
                    await self.program_repo.upsert(p)
                    saved += 1

            job.status = JobStatus.SUCCESS
            job.items_fetched = len(programs)
            job.items_saved = saved
            job.finished_at = datetime.now(tz=UTC)
            await self.job_repo.update(job)
            log.info(
                "aggregation.success",
                source_id=source.id,
                fetched=len(programs),
                saved=saved,
            )
            return job
        except Exception as e:
            job.status = JobStatus.PARTIAL_FAILURE if saved > 0 else JobStatus.FAILED
            job.error = str(e)[:1000]
            job.finished_at = datetime.now(tz=UTC)
            job.items_saved = saved  # 实际提交数（事务路径下失败时 saved=0）
            await self.job_repo.update(job)
            log.error(
                "aggregation.failed",
                source_id=source.id,
                saved=saved,
                error=str(e),
            )
            raise

    def _apply_norm(self, p: TVProgram) -> TVProgram:
        p.title = self.normalizer.normalize_title(p.title)
        return p
