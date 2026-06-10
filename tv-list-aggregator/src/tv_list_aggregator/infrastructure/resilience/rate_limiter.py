"""令牌桶限流（异步安全）。"""
from __future__ import annotations

import asyncio
import time


class TokenBucket:
    """异步令牌桶：每分钟 N 个令牌，按时间平滑补充。"""

    def __init__(self, rate_per_min: int) -> None:
        self.capacity = float(rate_per_min)
        self.tokens = float(rate_per_min)
        self.refill_rate = rate_per_min / 60.0
        self.last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last = now
            if self.tokens < 1:
                sleep_for = (1 - self.tokens) / self.refill_rate
                await asyncio.sleep(sleep_for)
                self.tokens = 0.0
            else:
                self.tokens -= 1.0
