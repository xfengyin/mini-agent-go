"""健康检查结果值对象。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceHealth(BaseModel):
    """单次数据源健康检查结果。"""

    model_config = ConfigDict(extra="ignore", frozen=True)

    source_id: str
    is_alive: bool
    latency_ms: int | None
    checked_at: datetime
    message: str | None = None
