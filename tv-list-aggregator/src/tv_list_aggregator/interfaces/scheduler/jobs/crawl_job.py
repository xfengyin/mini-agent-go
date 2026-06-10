"""抓取任务入口：遍历活跃源执行一次聚合。"""
from __future__ import annotations

from ....core.logging import get_logger
from ....domain.services.aggregation_service import AggregationService
from ....domain.services.source_registry import SourceRegistry

log = get_logger(__name__)


async def crawl_all_active(agg: AggregationService, registry: SourceRegistry) -> None:
    sources = await registry.active()
    for s in sources:
        try:
            await agg.run_once(s)
        except Exception as e:  # noqa: BLE001
            log.warning("crawl.skip_source", source_id=s.id, error=str(e))
