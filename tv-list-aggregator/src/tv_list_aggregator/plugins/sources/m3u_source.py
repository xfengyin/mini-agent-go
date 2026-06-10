"""M3U 直播/点播源适配器。

修复 issue #8：identity_key 改用稳定键 (source_id|channel_id|url_hash)，
避免每次抓取产生重复的 TVProgram 行。
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from ...core.exceptions import ParseError
from ...domain.models.program import TVProgram
from ...domain.models.source import TVListSource
from ...domain.models.value_objects import Channel, TimeSlot
from ...domain.ports.fetcher import Fetcher, FetchResult


def _stable_m3u_key(source_id: str, channel_id: str, url: str) -> str:
    """M3U 条目的稳定身份键：跨多次抓取保持不变，便于 upsert 去重。

    注：sha1 用作非密码学 ID 哈希（仅去重与稳定主键），不涉及安全场景。
    """
    raw = f"m3u|{source_id}|{channel_id}|{url}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()  # noqa: S324


class M3USource:
    """解析 M3U/M3U8 文件为频道集合（每条 EXTINF 作为占位 TVProgram，时间槽为占位 1h）。"""

    type = "m3u"

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    async def fetch(self, source: TVListSource) -> FetchResult:
        if not source.url:
            raise ValueError(f"source {source.id} has no url")
        return await self.fetcher.fetch(str(source.url), headers=source.headers or None)

    async def parse(self, result: FetchResult, source: TVListSource) -> list[TVProgram]:
        text = result.body.decode("utf-8", errors="ignore")
        if "#EXTM3U" not in text:
            raise ParseError("not a valid m3u file")
        # M3U 没有节目时间。改用"抓取时刻向前对齐到天"作为占位 slot，
        # 这样同一 source 的同一条目 identity_key 在同一天内稳定（跨天也仅滚动一次）。
        now = datetime.now(tz=UTC)
        epoch_day = datetime(now.year, now.month, now.day, tzinfo=UTC)
        end = epoch_day.replace(hour=23, minute=59, second=59)
        programs: list[TVProgram] = []
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("#EXTINF"):
                # 解析 tvg-id 与频道名
                name = line.split(",", 1)[-1].strip() if "," in line else "unknown"
                tvg = ""
                if 'tvg-id="' in line:
                    tvg = line.split('tvg-id="', 1)[1].split('"', 1)[0]
                # 找下一行 URL
                url = ""
                if i + 1 < len(lines):
                    url = lines[i + 1].strip()
                    i += 2
                else:
                    i += 1
                channel_id = tvg or name
                ch = Channel(id=channel_id, name=name)
                # 显式使用稳定 identity_key，绕过 title+start 派生
                identity_key = _stable_m3u_key(source.id, channel_id, url)
                programs.append(
                    TVProgram(
                        id=str(uuid4()),
                        title=f"{name} (m3u entry)",
                        description=url,
                        channel=ch,
                        slot=TimeSlot(start=epoch_day, end=end),
                        source_ids=[source.id],
                        identity_key=identity_key,
                        created_at=now,
                        updated_at=now,
                    )
                )
            else:
                i += 1
        return programs
