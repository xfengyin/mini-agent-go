"""Ollama 本地 LLM 适配器（HTTP 协议）。"""
from __future__ import annotations

import os

import httpx

from ...core.exceptions import LLMError
from ...domain.ports.llm import LLM


class OllamaAdapter(LLM):
    """Ollama 本地 LLM 适配器（/api/generate, /api/embeddings）。"""

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        url = base_url if base_url is not None else os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.base_url = url.rstrip("/")
        m = model if model is not None else os.getenv("OLLAMA_MODEL", "llama3")
        self.model = m
        self._client = httpx.AsyncClient(timeout=120.0)

    async def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        try:
            r = await self._client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False, "format": "json" if json_mode else None},
            )
            r.raise_for_status()
            data: object = r.json()
            return str(data.get("response", "")) if isinstance(data, dict) else ""  # type: ignore[union-attr]
        except Exception as e:  # noqa: BLE001
            raise LLMError(str(e)) from e

    async def embed(self, text: str) -> list[float]:
        try:
            r = await self._client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
            r.raise_for_status()
            data: object = r.json()
            emb: object = data.get("embedding", []) if isinstance(data, dict) else []  # type: ignore[union-attr]
            return list(emb)  # type: ignore[arg-type]
        except Exception as e:  # noqa: BLE001
            raise LLMError(str(e)) from e

    async def aclose(self) -> None:
        await self._client.aclose()
