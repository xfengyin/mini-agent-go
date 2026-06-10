"""多 LLM Provider 兜底路由：primary 失败后顺序尝试 fallbacks。"""
from __future__ import annotations

import asyncio

from ...core.exceptions import LLMError
from ...core.logging import get_logger
from ...domain.ports.llm import LLM

log = get_logger(__name__)


class LLMRouter(LLM):
    """Provider 链式兜底：primary -> fallbacks。"""

    def __init__(self, primary: LLM, fallbacks: list[LLM] | None = None) -> None:
        self.primary = primary
        self.fallbacks = fallbacks or []

    async def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        chain: list[LLM] = [self.primary, *self.fallbacks]
        last_err: Exception | None = None
        for idx, llm in enumerate(chain):
            try:
                return await llm.complete(prompt, json_mode=json_mode)
            except LLMError as e:
                last_err = e
                log.warning("llm.failure", provider_index=idx, error=str(e))
                await asyncio.sleep(0.2 * (idx + 1))
        raise LLMError(f"all llm providers failed: {last_err}")

    async def embed(self, text: str) -> list[float]:
        return await self.primary.embed(text)
