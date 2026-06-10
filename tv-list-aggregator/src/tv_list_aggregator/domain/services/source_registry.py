"""源注册中心：启停控制 + 失败自动暂停。"""
from __future__ import annotations

from ..models.source import SourceStatus, TVListSource
from ..ports.source_repository import SourceRepository


class SourceRegistry:
    """活跃源查询与启停切换。"""

    def __init__(self, repo: SourceRepository) -> None:
        self.repo = repo

    async def active(self) -> list[TVListSource]:
        return await self.repo.list(status=SourceStatus.ACTIVE.value)

    async def all(self) -> list[TVListSource]:
        return await self.repo.list()

    async def enable(self, source_id: str) -> None:
        s = await self.repo.get(source_id)
        if s:
            s.status = SourceStatus.ACTIVE
            await self.repo.update(s)

    async def disable(self, source_id: str) -> None:
        s = await self.repo.get(source_id)
        if s:
            s.status = SourceStatus.DISABLED
            await self.repo.update(s)

    async def pause(self, source_id: str) -> None:
        s = await self.repo.get(source_id)
        if s:
            s.status = SourceStatus.PAUSED
            await self.repo.update(s)
