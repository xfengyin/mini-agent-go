"""Scheduler jobs 单元测试：health_check 持久化、auto-pause 逻辑。"""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tv_list_aggregator.domain.models.health import SourceHealth
from tv_list_aggregator.domain.models.source import SourceStatus, SourceType, TVListSource
from tv_list_aggregator.domain.services.health_check_service import HealthCheckService
from tv_list_aggregator.domain.services.source_registry import SourceRegistry
from tv_list_aggregator.infrastructure.persistence.models import Base
from tv_list_aggregator.infrastructure.persistence.source_health_repository import (
    SQLAlchemySourceHealthRepository,
)
from tv_list_aggregator.infrastructure.persistence.source_repository_impl import (
    SQLAlchemySourceRepository,
)
from tv_list_aggregator.interfaces.scheduler.jobs.health_check_job import health_check_loop


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_health_check_pauses_after_threshold(session_factory) -> None:
    # 准备源（active）
    async with session_factory() as session:
        repo = SQLAlchemySourceRepository(session)
        await repo.add(
            TVListSource(
                id="s1",
                name="src1",
                type=SourceType.HTTP_JSON,
                url="https://broken.local",
                cron="*/5 * * * *",
                parser="json",
                status=SourceStatus.ACTIVE,
                created_at=datetime.now(tz=UTC),
                updated_at=datetime.now(tz=UTC),
            )
        )
        await session.commit()

    # mock health service：永远不健康
    failing_svc = AsyncMock(spec=HealthCheckService)
    failing_svc.check = AsyncMock(
        return_value=SourceHealth(
            source_id="s1",
            is_alive=False,
            latency_ms=10,
            message="down",
            checked_at=datetime.now(tz=UTC),
        )
    )

    threshold = 3
    # 复用同 session 跑 3 次（模拟 3 次 cron 触发）
    for i in range(threshold):
        async with session_factory() as session:
            src_repo = SQLAlchemySourceRepository(session)
            health_repo = SQLAlchemySourceHealthRepository(session)
            registry = SourceRegistry(src_repo)
            await health_check_loop(
                svc=failing_svc, registry=registry, source_repo=src_repo, health_repo=health_repo
            )
            await session.commit()
        # 关键断言：fail_streak 跨任务持久化
        async with session_factory() as session2:
            health_repo2 = SQLAlchemySourceHealthRepository(session2)
            streak = await health_repo2.get_streak("s1")
            assert streak == i + 1, f"after {i + 1} runs, expected streak {i + 1}, got {streak}"

    # 第 3 次后源应被自动 pause
    async with session_factory() as session3:
        src_repo3 = SQLAlchemySourceRepository(session3)
        s = await src_repo3.get("s1")
        assert s is not None
        assert s.status == SourceStatus.PAUSED


@pytest.mark.asyncio
async def test_health_check_resets_streak_when_alive(session_factory) -> None:
    async with session_factory() as session:
        repo = SQLAlchemySourceRepository(session)
        await repo.add(
            TVListSource(
                id="s2",
                name="s2",
                type=SourceType.HTTP_JSON,
                url="https://ok.local",
                cron="*/5 * * * *",
                parser="json",
                status=SourceStatus.ACTIVE,
                created_at=datetime.now(tz=UTC),
                updated_at=datetime.now(tz=UTC),
            )
        )
        await session.commit()

    ok_svc = AsyncMock(spec=HealthCheckService)
    ok_svc.check = AsyncMock(
        return_value=SourceHealth(
            source_id="s2",
            is_alive=True,
            latency_ms=5,
            message="ok",
            checked_at=datetime.now(tz=UTC),
        )
    )
    async with session_factory() as session:
        src_repo = SQLAlchemySourceRepository(session)
        health_repo = SQLAlchemySourceHealthRepository(session)
        # 先积累 2 次失败
        await health_repo.increment("s2", "down")
        await health_repo.increment("s2", "down")
        assert await health_repo.get_streak("s2") == 2
        # 健康 tick 应清零
        registry = SourceRegistry(src_repo)
        await health_check_loop(
            svc=ok_svc, registry=registry, source_repo=src_repo, health_repo=health_repo
        )
        assert await health_repo.get_streak("s2") == 0
        await session.commit()
