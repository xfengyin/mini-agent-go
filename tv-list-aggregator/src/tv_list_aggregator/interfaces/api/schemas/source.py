"""Source DTO。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from ....domain.models.source import SourceStatus, SourceType


class SourceCreate(BaseModel):
    id: str | None = Field(default=None, description="可选，客户端幂等 ID；缺省时服务端生成 UUID")
    name: str
    type: SourceType
    url: str | None = None  # 接受任意字符串，URL 校验放到 fetcher 层
    config: dict = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    cron: str = "*/15 * * * *"
    priority: int = 5
    parser: str = "auto"


class SourceUpdate(BaseModel):
    """PUT /sources/{id} 的请求体，所有字段可选，支持部分更新。"""
    name: str | None = None
    type: SourceType | None = None
    url: str | None = None
    config: dict | None = None
    headers: dict[str, str] | None = None
    cron: str | None = None
    priority: int | None = None
    parser: str | None = None


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: SourceType
    url: HttpUrl | None
    cron: str
    priority: int
    status: SourceStatus
    parser: str
    created_at: datetime
    updated_at: datetime
