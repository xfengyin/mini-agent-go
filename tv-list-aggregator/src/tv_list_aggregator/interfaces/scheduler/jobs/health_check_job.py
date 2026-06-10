"""健康检查任务：连续失败阈值触发自动暂停。"""
from __future__ import annotations

from .....core.logging import get_logger
from .....core.settings import get_settings
from .....domain.models.source import SourceStatus
from .....domain.ports.source_repository import SourceRepository
from .....domain.services.health_check_service import HealthCheckService
from .....domain.services.source_registry import SourceRegistry

log = get_logger(__name__)


async def health_check_loop(
    svc: HealthCheckService,
    registry: SourceRegistry,
    repo: SourceRepository,
) -> None:
    threshold = get_settings().health_check_fail_threshold
    fail_streak: dict[str, int] = {}
    sources = await registry.active()
    for s in sources:
        h = await svc.check(s)
        if not h.is_alive:
            fail_streak[s.id] = fail_streak.get(s.id, 0) + 1
            log.warning(
                "health.fail", source_id=s.id, streak=fail_streak[s.id], message=h.message
            )
            if fail_streak[s.id] >= threshold:
                s.status = SourceStatus.PAUSED
                await repo.update(s)
                log.warning("source.auto_paused", source_id=s.id, streak=fail_streak[s.id])
        else:
            fail_streak.pop(s.id, None)
