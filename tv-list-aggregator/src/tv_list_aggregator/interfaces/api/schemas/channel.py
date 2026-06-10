"""频道 DTO。"""
from __future__ import annotations

from pydantic import BaseModel


class ChannelOut(BaseModel):
    channel_id: str
    channel_name: str
    channel_country: str | None = None
    channel_language: str | None = None
    program_count: int
