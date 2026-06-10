"""LLM 路由与 Prompt 加载器测试。"""
from __future__ import annotations

import pytest

from tv_list_aggregator.core.exceptions import LLMError
from tv_list_aggregator.infrastructure.llm.llm_router import LLMRouter
from tv_list_aggregator.infrastructure.llm.prompt_loader import PromptLoader


class _FakeLLM:
    def __init__(self, fail: bool, out: str = "ok") -> None:
        self.fail = fail
        self.out = out

    async def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        if self.fail:
            raise LLMError("boom")
        return self.out

    async def embed(self, text: str) -> list[float]:
        return [0.0]


@pytest.mark.asyncio
async def test_router_fallback_chain() -> None:
    router = LLMRouter(primary=_FakeLLM(fail=True), fallbacks=[_FakeLLM(fail=True), _FakeLLM(fail=False, out="ok2")])
    assert await router.complete("hi") == "ok2"


@pytest.mark.asyncio
async def test_router_all_fail_raises() -> None:
    router = LLMRouter(primary=_FakeLLM(fail=True), fallbacks=[_FakeLLM(fail=True)])
    with pytest.raises(LLMError):
        await router.complete("hi")


def test_prompt_loader_renders_var() -> None:
    loader = PromptLoader("src/tv_list_aggregator/infrastructure/llm/prompts")
    out = loader.render("normalize", payload='{"title":" X "}')
    assert "X" in out
