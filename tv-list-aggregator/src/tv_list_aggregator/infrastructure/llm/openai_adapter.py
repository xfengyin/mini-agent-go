"""OpenAI 适配器。"""
from __future__ import annotations

import os
from typing import Any

from openai import AsyncOpenAI

from ...core.exceptions import LLMError
from ...domain.ports.llm import LLM


class OpenAIAdapter(LLM):
    """基于 openai SDK 的 LLM 适配器。"""

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY", ""))

    async def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        try:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            r = await self._client.chat.completions.create(**kwargs)
            content = r.choices[0].message.content
            return content if content is not None else ""
        except Exception as e:  # noqa: BLE001
            raise LLMError(str(e)) from e

    async def embed(self, text: str) -> list[float]:
        try:
            r = await self._client.embeddings.create(model="text-embedding-3-small", input=text)
            return list(r.data[0].embedding)
        except Exception as e:  # noqa: BLE001
            raise LLMError(str(e)) from e
