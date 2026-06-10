"""Anthropic Claude 适配器。"""
from __future__ import annotations

import os
from typing import Any

from ...core.exceptions import LLMError
from ...domain.ports.llm import LLM


class AnthropicAdapter(LLM):
    """基于 anthropic SDK 的 LLM 适配器。"""

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

    async def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self._api_key)
            msg = await client.messages.create(
                model=self.model,  # type: ignore[arg-type]
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            # 提取 text 块
            parts: list[str] = []
            for b in msg.content:
                block: Any = b
                if getattr(block, "type", None) == "text":
                    text_val: object = getattr(block, "text", "")
                    parts.append(str(text_val))
            return "\n".join(parts)
        except Exception as e:  # noqa: BLE001
            raise LLMError(str(e)) from e

    async def embed(self, text: str) -> list[float]:
        raise LLMError("Anthropic does not provide embeddings in this adapter; use OpenAI/Ollama")
