"""源健康仓储：fail_streak 跨任务持久化。"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import SourceHealthRow


class SQLAlchemySourceHealthRepository:
    """聚合根 SourceHealth 仓储（不属于核心域 Port；作为 health-check 任务的实现细节）。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_streak(self, source_id: str) -> int:
        row = await self.session.get(SourceHealthRow, source_id)
        return row.fail_streak if row else 0

    async def increment(self, source_id: str, message: str | None = None) -> int:
        row = await self.session.get(SourceHealthRow, source_id)
        if row is None:
            row = SourceHealthRow(
                source_id=source_id, fail_streak=1, last_check_at=datetime.now(UTC), last_message=message
            )
            self.session.add(row)
        else:
            row.fail_streak += 1
            row.last_check_at = datetime.now(UTC)
            row.last_message = message
        await self.session.flush()
        return row.fail_streak

    async def reset(self, source_id: str) -> None:
        row = await self.session.get(SourceHealthRow, source_id)
        if row is not None:
            row.fail_streak = 0
            row.last_check_at = datetime.now(UTC)
            row.last_message = "ok"
            await self.session.flush()

    async def list_streaks(self) -> dict[str, int]:
        rows = (await self.session.execute(select(SourceHealthRow))).scalars().all()
        return {r.source_id: r.fail_streak for r in rows}
