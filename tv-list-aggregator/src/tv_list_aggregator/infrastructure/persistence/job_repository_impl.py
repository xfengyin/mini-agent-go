"""任务仓储 SQLAlchemy 实现。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.models.crawl_job import CrawlJob, JobStatus
from ...domain.ports.job_repository import JobRepository
from .models import JobRow


class SQLAlchemyJobRepository(JobRepository):
    """基于 SQLAlchemy 的 Job 仓储实现。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_domain(r: JobRow) -> CrawlJob:
        return CrawlJob(
            id=r.id,
            source_id=r.source_id,
            status=JobStatus(r.status),
            started_at=r.started_at,
            finished_at=r.finished_at,
            items_fetched=r.items_fetched,
            items_saved=r.items_saved,
            error=r.error,
            trace_id=r.trace_id,
        )

    async def add(self, job: CrawlJob) -> None:
        self.session.add(
            JobRow(
                id=job.id,
                source_id=job.source_id,
                status=job.status.value,
                started_at=job.started_at,
                finished_at=job.finished_at,
                items_fetched=job.items_fetched,
                items_saved=job.items_saved,
                error=job.error,
                trace_id=job.trace_id,
            )
        )

    async def update(self, job: CrawlJob) -> None:
        row = await self.session.get(JobRow, job.id)
        if not row:
            return
        row.status = job.status.value
        row.finished_at = job.finished_at
        row.items_fetched = job.items_fetched
        row.items_saved = job.items_saved
        row.error = job.error
        row.trace_id = job.trace_id

    async def list(
        self,
        *,
        source_id: str | None = None,
        status: JobStatus | None = None,
        limit: int = 50,
    ) -> list[CrawlJob]:
        stmt = select(JobRow).order_by(JobRow.started_at.desc()).limit(limit)
        if source_id:
            stmt = stmt.where(JobRow.source_id == source_id)
        if status:
            stmt = stmt.where(JobRow.status == status.value)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]
