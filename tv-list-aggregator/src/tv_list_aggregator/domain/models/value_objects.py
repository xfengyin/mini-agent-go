"""不可变值对象：频道、时间槽、标签、归一化键。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Channel(BaseModel):
    """频道值对象。"""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    logo_url: HttpUrl | None = None
    country: str | None = None
    language: str | None = None


class TimeSlot(BaseModel):
    """节目播放时段。"""

    model_config = ConfigDict(frozen=True)

    start: datetime
    end: datetime
    timezone: str = "UTC"


class Tag(BaseModel):
    """节目标签（类型/地区/语言等）。"""

    model_config = ConfigDict(frozen=True)

    label: str
    category: str  # "genre" | "region" | "language" | "rating"


class ProgramIdentity(BaseModel):
    """跨源去重键：title+channel+start。"""

    model_config = ConfigDict(frozen=True)

    title_norm: str
    channel_id: str
    start: datetime
