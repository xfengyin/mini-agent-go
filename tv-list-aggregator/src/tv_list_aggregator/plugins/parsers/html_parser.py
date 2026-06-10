"""HTML 解析器：使用 trafilatura 抽取正文，作为 LLM 解析的预处理。"""
from __future__ import annotations

import trafilatura

from ...core.exceptions import ParseError
from ...domain.models.program import TVProgram


class HTMLParser:
    """HTML 解析器：抽取正文文本，供后续 LLM 解析或规则抽取。"""

    name = "html"

    async def parse(self, content: bytes, *, hint: dict | None = None) -> list[TVProgram]:
        text = trafilatura.extract(content.decode("utf-8", errors="ignore")) or ""
        if not text:
            raise ParseError("no extractable text from html")
        # HTML 解析器不直接产出结构化节目，由 LLM 解析器兜底
        return []
