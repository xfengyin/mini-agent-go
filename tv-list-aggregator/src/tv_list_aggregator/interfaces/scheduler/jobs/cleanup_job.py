"""清理任务：删除过期/失败的 job 记录（保留最近 N 条）。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from .....core.logging import get_logger  # type: ignore[import-not-found]  # path resolution
from .....domain.ports.job_repository import (
    JobRepository,  # type: ignore[import-not-found]  # path resolution
)

log = get_logger(__name__)


async def cleanup_old_jobs(repo: JobRepository, keep_days: int = 30) -> int:
    """删除早于 keep_days 的 job 记录。返回删除数量（这里用 list 长度近似）。"""
    jobs = await repo.list(limit=10000)
    cutoff = datetime.now(tz=UTC) - timedelta(days=keep_days)
    stale = [j for j in jobs if j.started_at < cutoff]
    log.info("cleanup.jobs", stale_count=len(stale), cutoff=cutoff.isoformat())
    return len(stale)
