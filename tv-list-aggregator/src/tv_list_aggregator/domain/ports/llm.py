"""LLM 端口：抽象大模型调用能力。"""
from __future__ import annotations

from typing import Protocol


class LLM(Protocol):
    """LLM 接口（文本补全 + Embedding）。"""

    async def complete(self, prompt: str, *, json_mode: bool = False) -> str: ...
    async def embed(self, text: str) -> list[float]: ...
