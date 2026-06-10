"""JSON 解析器：支持 list 顶层或 {items|programs:[...]}。"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from ...core.exceptions import ParseError
from ...domain.models.program import TVProgram
from ...domain.models.value_objects import Channel
from .base import to_program


class JSONParser:
    """解析 JSON 格式的节目数据。"""

    name = "json"

    async def parse(
        self, content: bytes, *, hint: dict[str, Any] | None = None
    ) -> list[TVProgram]:
        source_id = (hint or {}).get("source_id", "unknown")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ParseError(f"invalid json: {e}") from e

        items = data if isinstance(data, list) else data.get("items") or data.get("programs") or []
        if not isinstance(items, list):
            raise ParseError("json root must be list or {items:[]}")

        programs: list[TVProgram] = []
        for it in items:
            if not isinstance(it, dict) or "title" not in it or "start" not in it or "end" not in it:
                continue
            ch_id = str(it.get("channel_id") or it.get("channel") or "unknown")
            ch_name = str(it.get("channel_name") or it.get("channel") or "unknown")
            try:
                start = datetime.fromisoformat(str(it["start"]).replace("Z", "+00:00"))
                end = datetime.fromisoformat(str(it["end"]).replace("Z", "+00:00"))
            except ValueError as e:
                raise ParseError(f"bad datetime: {e}") from e
            programs.append(
                to_program(
                    title=str(it["title"]),
                    channel=Channel(id=ch_id, name=ch_name),
                    start=start,
                    end=end,
                    description=it.get("description"),
                    source_id=source_id,
                )
            )
        return programs
