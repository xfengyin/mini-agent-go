"""解析器基类与工具：构造 TVProgram 的稳定入口。"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from ...domain.models.program import TVProgram
from ...domain.models.value_objects import Channel, TimeSlot


def make_identity_key(title: str, channel_id: str, start: datetime) -> str:
    """基于 title+channel+start 计算稳定身份键。"""
    raw = f"{title.strip().lower()}|{channel_id}|{start.isoformat()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def to_program(
    *,
    title: str,
    channel: Channel,
    start: datetime,
    end: datetime,
    description: str | None,
    source_id: str,
    tags: list | None = None,
) -> TVProgram:
    """统一的 TVProgram 构造入口。"""
    now = datetime.now(tz=UTC)
    return TVProgram(
        title=title.strip(),
        description=description,
        channel=channel,
        slot=TimeSlot(start=start, end=end),
        tags=tags or [],
        source_ids=[source_id],
        identity_key=make_identity_key(title, channel.id, start),
        created_at=now,
        updated_at=now,
    )
