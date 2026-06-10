"""节目仓储接口。"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from ..models.program import TVProgram


class ProgramRepository(Protocol):
    """节目仓储协议（upsert/list/count）。"""

    async def upsert(self, program: TVProgram) -> TVProgram: ...
    async def find_by_identity(self, identity_key: str) -> TVProgram | None: ...
    async def list_by_range(
        self, start: datetime, end: datetime, *, channel_id: str | None = None
    ) -> list[TVProgram]: ...
    async def count(self) -> int: ...
