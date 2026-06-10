"""Parser 端口：抽象内容解析能力。"""
from __future__ import annotations

from typing import Protocol

from ..models.program import TVProgram


class Parser(Protocol):
    """Parser 接口。"""

    name: str

    async def parse(self, content: bytes, *, hint: dict | None = None) -> list[TVProgram]: ...
