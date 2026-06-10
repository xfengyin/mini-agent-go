"""Job DTO。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ....domain.models.crawl_job import JobStatus


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    status: JobStatus
    started_at: datetime
    finished_at: datetime | None
    items_fetched: int
    items_saved: int
    error: str | None
    trace_id: str | None
