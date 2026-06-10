"""LLM 解析器：异构/弱结构内容的兜底抽取。"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from ...core.exceptions import LLMError, ParseError
from ...domain.models.program import TVProgram
from ...domain.models.value_objects import Channel
from ...domain.ports.llm import LLM
from ...infrastructure.llm.prompt_loader import PromptLoader
from .base import to_program


class LLMParser:
    """使用 LLM 从非结构化内容中抽取节目，作为最后兜底。"""

    name = "llm"

    def __init__(self, llm: LLM, prompts: PromptLoader) -> None:
        self.llm = llm
        self.prompts = prompts

    async def parse(
        self, content: bytes, *, hint: dict[str, Any] | None = None
    ) -> list[TVProgram]:
        source_id = (hint or {}).get("source_id", "unknown")
        text = content.decode("utf-8", errors="ignore")[:30000]
        prompt = self.prompts.render("extract_program", content=text)
        try:
            raw = await self.llm.complete(prompt, json_mode=True)
        except LLMError as e:
            raise ParseError(str(e)) from e

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            # 尝试提取 JSON 片段
            import re

            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise ParseError(f"llm returned non-json: {e}") from e
            data = json.loads(match.group(0))

        items = data if isinstance(data, list) else data.get("items") or data.get("programs") or []
        if not isinstance(items, list):
            raise ParseError("llm json root must be list or {items:[]}")

        programs: list[TVProgram] = []
        for it in items:
            if not isinstance(it, dict) or "title" not in it or "start" not in it or "end" not in it:
                continue
            ch = Channel(
                id=str(it.get("channel_id") or "unknown"),
                name=str(it.get("channel_name") or it.get("channel") or "unknown"),
            )
            try:
                start = datetime.fromisoformat(str(it["start"]).replace("Z", "+00:00"))
                end = datetime.fromisoformat(str(it["end"]).replace("Z", "+00:00"))
            except ValueError as e:
                raise ParseError(f"bad datetime from llm: {e}") from e
            programs.append(
                to_program(
                    title=str(it["title"]),
                    channel=ch,
                    start=start,
                    end=end,
                    description=it.get("description"),
                    source_id=source_id,
                )
            )
        return programs
