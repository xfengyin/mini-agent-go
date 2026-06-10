"""Clock 端口：抽象"当前时间"便于测试。"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """时钟接口。"""

    def now(self) -> datetime: ...


class SystemClock:
    """系统时钟默认实现。"""

    def now(self) -> datetime:

        return datetime.now(tz=UTC)
