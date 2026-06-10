"""任务查询路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ....domain.models.crawl_job import CrawlJob, JobStatus
from ....infrastructure.persistence.job_repository_impl import SQLAlchemyJobRepository
from ..deps import get_job_repo
from ..schemas.job import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
async def list_jobs(
    source_id: str | None = None,
    status_filter: JobStatus | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
    repo: SQLAlchemyJobRepository = Depends(get_job_repo),
) -> list[CrawlJob]:
    return await repo.list(source_id=source_id, status=status_filter, limit=limit)
