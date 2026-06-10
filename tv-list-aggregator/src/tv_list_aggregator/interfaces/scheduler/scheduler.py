"""APScheduler 异步调度器封装。"""
from __future__ import annotations

from collections.abc import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


class JobScheduler:
    """提供 cron/interval 两种触发方式，单实例合并。"""

    def __init__(self) -> None:
        self.sched = AsyncIOScheduler()

    def start(self) -> None:
        if not self.sched.running:
            self.sched.start()

    def shutdown(self) -> None:
        if self.sched.running:
            self.sched.shutdown(wait=False)

    def add_cron(self, job_id: str, cron: str, func: Callable) -> None:
        self.sched.add_job(
            func,
            CronTrigger.from_crontab(cron),
            id=job_id,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    def add_interval(self, job_id: str, seconds: int, func: Callable) -> None:
        self.sched.add_job(
            func,
            "interval",
            seconds=seconds,
            id=job_id,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    def remove(self, job_id: str) -> None:
        try:
            self.sched.remove_job(job_id)
        except Exception:
            pass
