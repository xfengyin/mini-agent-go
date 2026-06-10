"""标准化服务：大小写/空白/字段清洗。"""
from __future__ import annotations

import re


class NormalizationService:
    """对原始字段执行轻量级归一化。"""

    _WS = re.compile(r"\s+")

    def normalize_title(self, title: str) -> str:
        return self._WS.sub(" ", title).strip()

    def normalize_channel_id(self, channel_id: str) -> str:
        return channel_id.lower().strip()
