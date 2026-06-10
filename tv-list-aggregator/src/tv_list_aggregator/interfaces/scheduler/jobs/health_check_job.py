"""健康检查任务：使用 SourceHealthRepository 持久化 fail_streak。"""
from __future__ import annotations

from ....core.logging import get_logger
from ....core.settings import get_settings
from ....domain.models.source import SourceStatus
from ....domain.ports.source_repository import SourceRepository
from ....domain.services.health_check_service import HealthCheckService
from ....domain.services.source_registry import SourceRegistry
from ....infrastructure.persistence.source_health_repository import (
    SQLAlchemySourceHealthRepository,
)

log = get_logger(__name__)


async def health_check_loop(
    svc: HealthCheckService,
    registry: SourceRegistry,
    source_repo: SourceRepository,
    health_repo: SQLAlchemySourceHealthRepository,
) -> None:
    """遍历活跃源执行健康检查，连续失败达到阈值时自动暂停。

    修复 issue #1：fail_streak 通过 SourceHealthRepository 跨任务持久化。
    """
    threshold = get_settings().health_check_fail_threshold
    sources = await registry.active()
    for s in sources:
        h = await svc.check(s)
        if not h.is_alive:
            streak = await health_repo.increment(s.id, message=h.message)
            log.warning(
                "health.fail",
                source_id=s.id,
                streak=streak,
                threshold=threshold,
                message=h.message,
            )
            if streak >= threshold:
                s.status = SourceStatus.PAUSED
                await source_repo.update(s)
                log.warning("source.auto_paused", source_id=s.id, streak=streak)
        else:
            await health_repo.reset(s.id)
