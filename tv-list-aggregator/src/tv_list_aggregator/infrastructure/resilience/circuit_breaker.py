"""轻量级异步熔断器（替代 pybreaker，避免 Tornado 依赖）。"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TypeVar

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class AsyncCircuitBreaker:
    """三态熔断器：closed → open → half_open → closed/open。

    - closed：正常请求，连续失败 fail_max 次后切到 open
    - open：拒绝所有请求，reset_timeout 秒后进入 half_open
    - half_open：放行一个探测请求；成功回到 closed，失败回到 open
    """

    def __init__(self, name: str, fail_max: int = 5, reset_timeout: float = 30.0) -> None:
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self._state = CircuitState.CLOSED
        self._fail_count = 0
        self._opened_at: float | None = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    async def call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        async with self._lock:
            now = time.monotonic()
            if self._state is CircuitState.OPEN:
                assert self._opened_at is not None
                if now - self._opened_at >= self.reset_timeout:
                    self._state = CircuitState.HALF_OPEN
                else:
                    from ...core.exceptions import TransientError

                    raise TransientError(f"circuit '{self.name}' is open")

        try:
            result = await func(*args, **kwargs)
        except Exception:
            await self._on_failure()
            raise
        else:
            await self._on_success()
            return result

    async def _on_success(self) -> None:
        async with self._lock:
            if self._state is CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
            self._fail_count = 0
            self._opened_at = None

    async def _on_failure(self) -> None:
        async with self._lock:
            self._fail_count += 1
            if self._state is CircuitState.HALF_OPEN or self._fail_count >= self.fail_max:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
