"""标准化与源注册中心测试。"""
from __future__ import annotations

from datetime import UTC

import pytest

from tv_list_aggregator.domain.services.normalization_service import NormalizationService
from tv_list_aggregator.domain.services.source_registry import SourceRegistry


def test_normalize_title() -> None:
    n = NormalizationService()
    assert n.normalize_title("  Hello   World  ") == "Hello World"


class _RepoStub:
    def __init__(self) -> None:
        self.items: dict = {}

    async def get(self, source_id):
        return self.items.get(source_id)

    async def list(self, *, status=None):
        return [s for s in self.items.values() if not status or s.status.value == status]

    async def add(self, source):
        self.items[source.id] = source

    async def update(self, source):
        self.items[source.id] = source

    async def delete(self, source_id):
        self.items.pop(source_id, None)


@pytest.mark.asyncio
async def test_source_registry_active_and_disable() -> None:
    from datetime import datetime

    from tv_list_aggregator.domain.models.source import SourceStatus, SourceType, TVListSource

    repo = _RepoStub()
    reg = SourceRegistry(repo)
    now = datetime.now(tz=UTC)
    s1 = TVListSource(
        id="s1", name="A", type=SourceType.HTTP_JSON,
        status=SourceStatus.ACTIVE, created_at=now, updated_at=now,
    )
    s2 = TVListSource(
        id="s2", name="B", type=SourceType.HTTP_JSON,
        status=SourceStatus.DISABLED, created_at=now, updated_at=now,
    )
    await repo.add(s1)
    await repo.add(s2)

    active = await reg.active()
    assert {s.id for s in active} == {"s1"}

    await reg.disable("s1")
    assert (await reg.active()) == []
    await reg.enable("s1")
    assert len(await reg.active()) == 1
