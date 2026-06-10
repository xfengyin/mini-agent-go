"""EventBus 端口。"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus(Protocol):
    """事件总线接口。"""

    async def publish(self, topic: str, payload: Any) -> None: ...
    def subscribe(self, topic: str, handler: EventHandler) -> None: ...
