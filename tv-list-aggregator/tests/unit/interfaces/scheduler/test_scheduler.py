"""调度器启停测试（异步）。"""
from __future__ import annotations

import pytest

from tv_list_aggregator.interfaces.scheduler.scheduler import JobScheduler


@pytest.mark.asyncio
async def test_scheduler_lifecycle() -> None:
    s = JobScheduler()
    s.start()
    try:
        assert s.sched.running
    finally:
        s.shutdown()
