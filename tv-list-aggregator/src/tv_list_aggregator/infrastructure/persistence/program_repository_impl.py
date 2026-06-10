"""节目仓储 SQLAlchemy 实现。"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.models.program import TVProgram
from ...domain.models.value_objects import Channel, Tag, TimeSlot
from ...domain.ports.program_repository import ProgramRepository
from .models import ProgramRow


class SQLAlchemyProgramRepository(ProgramRepository):
    """基于 SQLAlchemy 的 Program 仓储实现（upsert 基于 identity_key）。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_domain(r: ProgramRow) -> TVProgram:
        tags_raw: list[object] = r.tags or []
        tag_models: list[Tag] = []
        for t in tags_raw:
            if isinstance(t, dict) and "label" in t and "category" in t:
                label_obj: object = t["label"]
                category_obj: object = t["category"]
                tag_models.append(
                    Tag(label=str(label_obj), category=str(category_obj))
                )
        return TVProgram(
            id=r.id,
            title=r.title,
            description=r.description,
            channel=Channel(
                id=r.channel_id,
                name=r.channel_name,
                logo_url=r.channel_logo,
                country=r.channel_country,
                language=r.channel_language,
            ),
            slot=TimeSlot(start=r.start_at, end=r.end_at, timezone=r.timezone),
            tags=tag_models,
            source_ids=r.source_ids or [],
            identity_key=r.identity_key,
            created_at=r.created_at,
            updated_at=r.updated_at,
            version=r.version,
        )

    @staticmethod
    def _from_domain(p: TVProgram) -> ProgramRow:
        return ProgramRow(
            id=p.id or "",
            title=p.title,
            description=p.description,
            channel_id=p.channel.id,
            channel_name=p.channel.name,
            channel_logo=str(p.channel.logo_url) if p.channel.logo_url else None,
            channel_country=p.channel.country,
            channel_language=p.channel.language,
            start_at=p.slot.start,
            end_at=p.slot.end,
            timezone=p.slot.timezone,
            tags=[t.model_dump() for t in p.tags],
            source_ids=p.source_ids,
            identity_key=p.identity_key,
            version=p.version,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )

    async def upsert(self, program: TVProgram) -> TVProgram:
        existing = (
            await self.session.execute(
                select(ProgramRow).where(ProgramRow.identity_key == program.identity_key)
            )
        ).scalar_one_or_none()
        if existing:
            existing.title = program.title
            existing.description = program.description
            existing.start_at = program.slot.start
            existing.end_at = program.slot.end
            existing.tags = [t.model_dump() for t in program.tags]
            existing.source_ids = sorted({*(existing.source_ids or []), *program.source_ids})
            existing.version += 1
            existing.updated_at = datetime.now(tz=UTC)
            await self.session.flush()
            return self._to_domain(existing)
        row = self._from_domain(program)
        self.session.add(row)
        await self.session.flush()
        return self._to_domain(row)

    async def find_by_identity(self, identity_key: str) -> TVProgram | None:
        row = (
            await self.session.execute(
                select(ProgramRow).where(ProgramRow.identity_key == identity_key)
            )
        ).scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def list_by_range(
        self, start: datetime, end: datetime, *, channel_id: str | None = None
    ) -> list[TVProgram]:
        stmt = select(ProgramRow).where(
            ProgramRow.start_at >= start, ProgramRow.start_at < end
        )
        if channel_id:
            stmt = stmt.where(ProgramRow.channel_id == channel_id)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def count(self) -> int:
        return (
            await self.session.execute(select(func.count(ProgramRow.id)))
        ).scalar_one()
