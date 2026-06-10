"""Scheduler jobs 单元测试：crawl_all_active 编排与异常隔离。"""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tv_list_aggregator.domain.models.crawl_job import CrawlJob, JobStatus
from tv_list_aggregator.domain.models.source import SourceStatus, SourceType, TVListSource
from tv_list_aggregator.domain.services.source_registry import SourceRegistry
from tv_list_aggregator.infrastructure.persistence.models import Base
from tv_list_aggregator.infrastructure.persistence.source_repository_impl import (
    SQLAlchemySourceRepository,
)
from tv_list_aggregator.interfaces.scheduler.jobs.crawl_job import crawl_all_active


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_crawl_all_active_isolates_failures(session_factory) -> None:
    """crawl_all_active 应当：依次调用每个活跃源；任一失败不影响其他源。"""
    # 准备 2 个活跃源
    async with session_factory() as session:
        repo = SQLAlchemySourceRepository(session)
        for sid in ("good", "bad"):
            await repo.add(
                TVListSource(
                    id=sid,
                    name=sid,
                    type=SourceType.HTTP_JSON,
                    url=f"https://{sid}.local",
                    cron="*/5 * * * *",
                    parser="json",
                    status=SourceStatus.ACTIVE,
                    created_at=datetime.now(tz=UTC),
                    updated_at=datetime.now(tz=UTC),
                )
            )
        await session.commit()

    # agg mock：good 成功，bad 抛错
    agg = MagicMock()

    async def run_once_side_effect(src):
        if src.id == "bad":
            raise RuntimeError("simulated failure")
        return CrawlJob(
            id=f"job-{src.id}",
            source_id=src.id,
            status=JobStatus.SUCCESS,
            started_at=datetime.now(tz=UTC),
        )

    agg.run_once = AsyncMock(side_effect=run_once_side_effect)

    async with session_factory() as session:
        repo = SQLAlchemySourceRepository(session)
        registry = SourceRegistry(repo)
        # crawl_all_active 内部 try/except 隔离失败：两个源都被调用
        await crawl_all_active(agg, registry)

    assert agg.run_once.await_count == 2
