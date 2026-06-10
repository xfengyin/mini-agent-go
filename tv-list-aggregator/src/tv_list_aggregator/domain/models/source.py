"""数据源实体。"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SourceType(str, Enum):
    """数据源类型枚举。"""

    HTTP_JSON = "http_json"
    RSS = "rss"
    HTML_SCRAPE = "html_scrape"
    M3U = "m3u"
    CUSTOM = "custom"


class SourceStatus(str, Enum):
    """数据源运行状态。"""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class TVListSource(BaseModel):
    """数据源实体。"""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str = Field(min_length=1, max_length=255)
    type: SourceType
    url: str | None = None  # 接受任意字符串；具体 URL 校验由 fetcher 层负责
    config: dict = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    cron: str = "*/15 * * * *"
    priority: int = Field(default=5, ge=0, le=10)
    status: SourceStatus = SourceStatus.ACTIVE
    parser: str = "auto"
    created_at: datetime
    updated_at: datetime
