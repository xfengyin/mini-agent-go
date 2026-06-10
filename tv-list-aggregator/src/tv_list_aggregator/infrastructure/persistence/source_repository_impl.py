"""数据源仓储 SQLAlchemy 实现。"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.models.source import SourceStatus, SourceType, TVListSource
from ...domain.ports.source_repository import SourceRepository
from .models import SourceRow


class SQLAlchemySourceRepository(SourceRepository):
    """基于 SQLAlchemy 的 Source 仓储实现。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_domain(row: SourceRow) -> TVListSource:
        return TVListSource(
            id=row.id,
            name=row.name,
            type=SourceType(row.type),
            url=row.url,
            config=row.config or {},
            headers=row.headers or {},
            cron=row.cron,
            priority=row.priority,
            status=SourceStatus(row.status),
            parser=row.parser,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get(self, source_id: str) -> TVListSource | None:
        row = await self.session.get(SourceRow, source_id)
        return self._to_domain(row) if row else None

    async def list(self, *, status: str | None = None) -> list[TVListSource]:
        stmt = select(SourceRow)
        if status:
            stmt = stmt.where(SourceRow.status == status)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def add(self, source: TVListSource) -> None:
        self.session.add(
            SourceRow(
                id=source.id,
                name=source.name,
                type=source.type.value,
                url=str(source.url) if source.url else None,
                config=source.config,
                headers=source.headers,
                cron=source.cron,
                priority=source.priority,
                status=source.status.value,
                parser=source.parser,
                created_at=source.created_at,
                updated_at=source.updated_at,
            )
        )

    async def update(self, source: TVListSource) -> None:
        row = await self.session.get(SourceRow, source.id)
        if not row:
            return
        row.name = source.name
        row.type = source.type.value
        row.url = str(source.url) if source.url else None
        row.config = source.config
        row.headers = source.headers
        row.cron = source.cron
        row.priority = source.priority
        row.status = source.status.value
        row.parser = source.parser
        row.updated_at = datetime.now(tz=UTC)

    async def delete(self, source_id: str) -> None:
        row = await self.session.get(SourceRow, source_id)
        if row:
            await self.session.delete(row)
