"""抓取任务实体。"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(str, Enum):
    """抓取任务状态。"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"


class CrawlJob(BaseModel):
    """一次抓取任务的执行记录。"""

    model_config = ConfigDict(extra="ignore")

    id: str
    source_id: str
    status: JobStatus
    started_at: datetime
    finished_at: datetime | None = None
    items_fetched: int = 0
    items_saved: int = 0
    error: str | None = Field(default=None, max_length=2000)
    trace_id: str | None = None
