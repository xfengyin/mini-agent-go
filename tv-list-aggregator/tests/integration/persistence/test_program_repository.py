"""Program 仓储集成测试。"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tv_list_aggregator.domain.models.program import TVProgram
from tv_list_aggregator.domain.models.value_objects import Channel, TimeSlot
from tv_list_aggregator.infrastructure.persistence.models import Base
from tv_list_aggregator.infrastructure.persistence.program_repository_impl import (
    SQLAlchemyProgramRepository,
)


def _make_program(title: str = "X", identity: str = "k1") -> TVProgram:
    now = datetime.now(tz=UTC)
    return TVProgram(
        title=title,
        channel=Channel(id="c1", name="C1"),
        slot=TimeSlot(
            start=datetime(2026, 1, 1, 10, tzinfo=UTC),
            end=datetime(2026, 1, 1, 11, tzinfo=UTC),
        ),
        source_ids=["a"],
        identity_key=identity,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_program_upsert_and_count() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as s:
        repo = SQLAlchemyProgramRepository(s)
        p1 = _make_program()
        await repo.upsert(p1)
        await s.commit()
        assert await repo.count() == 1

        # 再次 upsert 同一 identity_key -> 应更新而非新增
        p2 = _make_program(title="X2")
        await repo.upsert(p2)
        await s.commit()
        assert await repo.count() == 1
        got = await repo.find_by_identity("k1")
        assert got is not None
        assert got.title == "X2"
        assert got.version == 2

    await engine.dispose()
