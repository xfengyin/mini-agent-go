"""进程内 TTL 缓存：线程安全 + 协程友好。

设计目标：
- 不引入新依赖（纯标准库实现）；
- 支持单次访问 get_or_set，避免重复计算（典型的"读多写少"热点数据场景）；
- 过期时间到点即失效（懒删除：访问时检查 expiry），避免后台清理线程带来的复杂度。

注意：
- 这是单进程内存缓存；多副本部署下命中率取决于请求路由；
- 适用：dashboard 聚合、配置中心、热点元数据等可容忍秒级不一致的读路径。
"""
from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class _Entry(Generic[T]):
    """缓存条目：值 + 过期时间（绝对 epoch 秒）。"""

    value: T
    expire_at: float


class TTLCache(Generic[T]):
    """线程 + 协程安全的 TTL 缓存。

    - 写入：set(key, value, ttl)；覆盖式写入。
    - 读取：get(key) 返回值或 None（过期/不存在）。
    - 复合：get_or_set(key, ttl, factory) 在缺失或过期时通过 factory 加载并回填。
    - 失效：invalidate(key) / clear()。

    并发模型：
    - asyncio.Lock 保证同 event loop 内协程安全；
    - threading.Lock 兜底覆盖同步调用或跨线程场景。
    """

    def __init__(self) -> None:
        self._store: dict[str, _Entry[T]] = {}
        self._aio_lock = asyncio.Lock()
        # threading.RLock：允许同线程重入（避免 clear() 在持锁时被 factory 重入触发死锁）
        self._thread_lock = threading.RLock()

    def get(self, key: str) -> T | None:
        """读取键。过期或不存在返回 None。"""
        now = time.monotonic()
        with self._thread_lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expire_at <= now:
                # 懒删除：访问时清理过期条目
                self._store.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: T, ttl: float) -> None:
        """写入键。ttl 单位为秒。"""
        expire_at = time.monotonic() + ttl
        with self._thread_lock:
            self._store[key] = _Entry(value=value, expire_at=expire_at)

    def invalidate(self, key: str) -> None:
        """主动失效一个键。"""
        with self._thread_lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """清空缓存。"""
        with self._thread_lock:
            self._store.clear()

    async def get_or_set(
        self,
        key: str,
        ttl: float,
        factory: Callable[[], Awaitable[T]],
    ) -> T:
        """读取或加载。

        命中：直接返回缓存值。
        未命中 / 过期：调用 factory() 异步加载并回填；同 key 并发只会触发一次 factory。
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        # 同一 key 的并发请求应只触发一次 factory：使用 asyncio.Lock 按 key 串行
        async with self._aio_lock:
            # 双检：进入锁后再次读，避免前一个等待者已回填
            cached = self.get(key)
            if cached is not None:
                return cached
            value = await factory()
            self.set(key, value, ttl)
            return value
