"""Program DTO。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProgramOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None
    title: str
    description: str | None
    channel_id: str
    channel_name: str
    start: datetime
    end: datetime
    timezone: str
    tags: list[dict] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    version: int
