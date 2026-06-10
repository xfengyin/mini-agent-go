"""Source DTO。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from ....domain.models.source import SourceStatus, SourceType


class SourceCreate(BaseModel):
    name: str
    type: SourceType
    url: HttpUrl | None = None
    config: dict = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    cron: str = "*/15 * * * *"
    priority: int = 5
    parser: str = "auto"


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
