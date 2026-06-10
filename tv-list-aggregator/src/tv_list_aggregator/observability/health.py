"""详细健康检查：聚合所有源状态。"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..domain.ports.source_repository import SourceRepository
from ..domain.services.health_check_service import HealthCheckService


async def detailed_health(
    repo: SourceRepository, health_svc: HealthCheckService
) -> dict[str, Any]:
    """逐源健康检查 + 汇总。"""
    sources = await repo.list()
    results: list[dict[str, Any]] = []
    for s in sources:
        h = await health_svc.check(s)
        results.append(
            {
                "source_id": s.id,
                "name": s.name,
                "status": s.status.value,
                "alive": h.is_alive,
                "latency_ms": h.latency_ms,
                "message": h.message,
            }
        )
    return {
        "checked_at": datetime.now(tz=UTC).isoformat(),
        "sources": results,
        "all_alive": all(r["alive"] for r in results) if results else True,
    }
