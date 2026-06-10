"""M3U 直播/点播源适配器。"""
from __future__ import annotations

from datetime import UTC

from ...core.exceptions import ParseError
from ...domain.models.program import TVProgram
from ...domain.models.source import TVListSource
from ...domain.models.value_objects import Channel
from ...domain.ports.fetcher import Fetcher, FetchResult


class M3USource:
    """解析 M3U/M3U8 文件为频道集合（每条 EXTINF 作为 Channel，节目时间槽使用文件 mtime）。"""

    type = "m3u"

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    async def fetch(self, source: TVListSource) -> FetchResult:
        if not source.url:
            raise ValueError(f"source {source.id} has no url")
        return await self.fetcher.fetch(str(source.url), headers=source.headers or None)

    async def parse(self, result: FetchResult, source: TVListSource) -> list[TVProgram]:
        from datetime import datetime, timedelta

        text = result.body.decode("utf-8", errors="ignore")
        if "#EXTM3U" not in text:
            raise ParseError("not a valid m3u file")
        start = datetime.now(tz=UTC)
        end = start + timedelta(hours=1)
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
                ch = Channel(id=tvg or name, name=name)
                # M3U 没有节目时间，将整个列表视为一个节目槽（占位）
                from ...plugins.parsers.base import to_program as _tp

                programs.append(
                    _tp(
                        title=f"{name} (m3u entry)",
                        channel=ch,
                        start=start,
                        end=end,
                        description=url,
                        source_id=source.id,
                    )
                )
            else:
                i += 1
        return programs
