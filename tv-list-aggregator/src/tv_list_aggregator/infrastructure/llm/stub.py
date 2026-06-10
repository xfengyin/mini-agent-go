"""LLM Stub：当未配置 API Key 时使用，返回简单的规则化输出。"""
from __future__ import annotations

from ...domain.ports.llm import LLM


class StubLLM(LLM):
    """无密钥环境的占位 LLM：从内容中按正则提取节目行（仅用于本地/测试）。"""

    name = "stub"

    async def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        # 不做真实抽取；返回空 JSON 数组，交给上层兜底
        if json_mode:
            return '{"items":[]}'
        return ""

    async def embed(self, text: str) -> list[float]:
        # 极简词袋哈希为 8 维向量
        return [float(len(text) % (i + 1)) for i in range(8)]
