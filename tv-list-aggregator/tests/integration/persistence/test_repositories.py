"""仓储集成测试（SQLite in-memory）。"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tv_list_aggregator.domain.models.source import SourceStatus, SourceType, TVListSource
from tv_list_aggregator.infrastructure.persistence.models import Base
from tv_list_aggregator.infrastructure.persistence.source_repository_impl import (
    SQLAlchemySourceRepository,
)


@pytest.mark.asyncio
async def test_source_crud_lifecycle() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as s:
        repo = SQLAlchemySourceRepository(s)
        now = datetime.now(tz=UTC)
        src = TVListSource(
            id="s1", name="Demo", type=SourceType.HTTP_JSON,
            cron="*/15 * * * *", status=SourceStatus.ACTIVE,
            created_at=now, updated_at=now,
        )
        await repo.add(src)
        await s.commit()

    async with Session() as s:
        repo = SQLAlchemySourceRepository(s)
        got = await repo.get("s1")
        assert got is not None
        assert got.name == "Demo"
        assert got.status == SourceStatus.ACTIVE

        # update
        got.name = "Demo2"
        got.status = SourceStatus.PAUSED
        await repo.update(got)
        await s.commit()

    async with Session() as s:
        repo = SQLAlchemySourceRepository(s)
        got = await repo.get("s1")
        assert got is not None
        assert got.name == "Demo2"
        assert got.status == SourceStatus.PAUSED

        await repo.delete("s1")
        await s.commit()

    async with Session() as s:
        repo = SQLAlchemySourceRepository(s)
        assert await repo.get("s1") is None

    await engine.dispose()
