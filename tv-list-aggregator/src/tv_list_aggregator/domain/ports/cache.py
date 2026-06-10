"""Cache 端口。"""
from __future__ import annotations

from typing import Protocol


class Cache(Protocol):
    """缓存接口。"""

    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, *, ttl: int = 60) -> None: ...
    async def delete(self, key: str) -> None: ...
