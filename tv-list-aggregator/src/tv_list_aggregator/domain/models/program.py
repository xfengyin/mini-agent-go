"""节目聚合根。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .value_objects import Channel, Tag, TimeSlot


class TVProgram(BaseModel):
    """TV 节目聚合根。"""

    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    channel: Channel
    slot: TimeSlot
    tags: list[Tag] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    identity_key: str
    created_at: datetime
    updated_at: datetime
    version: int = 1
