"""解析器单元测试。"""
from __future__ import annotations

import json

import pytest

from tv_list_aggregator.core.exceptions import LLMError, ParseError
from tv_list_aggregator.infrastructure.llm.prompt_loader import PromptLoader
from tv_list_aggregator.plugins.parsers.json_parser import JSONParser
from tv_list_aggregator.plugins.parsers.llm_parser import LLMParser


@pytest.mark.asyncio
async def test_json_parser_list() -> None:
    data = [
        {
            "title": "X",
            "channel": "C1",
            "start": "2026-01-01T10:00:00+00:00",
            "end": "2026-01-01T11:00:00+00:00",
            "description": "d",
        }
    ]
    p = JSONParser()
    out = await p.parse(json.dumps(data).encode(), hint={"source_id": "s1"})
    assert len(out) == 1
    assert out[0].title == "X"
    assert out[0].channel.id == "C1"
    assert out[0].source_ids == ["s1"]


@pytest.mark.asyncio
async def test_json_parser_wrapped() -> None:
    payload = {
        "items": [
            {
                "title": "Y",
                "channel_id": "c2",
                "start": "2026-01-01T10:00:00Z",
                "end": "2026-01-01T11:00:00Z",
            }
        ]
    }
    out = await JSONParser().parse(json.dumps(payload).encode())
    assert out[0].title == "Y" and out[0].channel.id == "c2"


@pytest.mark.asyncio
async def test_json_parser_invalid_json() -> None:
    with pytest.raises(ParseError):
        await JSONParser().parse(b"not-json")


class _StubLLM:
    def __init__(self, response: str) -> None:
        self.response = response

    async def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        return self.response

    async def embed(self, text: str) -> list[float]:
        return [0.0]


@pytest.mark.asyncio
async def test_llm_parser_success() -> None:
    payload = json.dumps(
        {
            "items": [
                {
                    "title": "LLM",
                    "channel_name": "C-LLM",
                    "start": "2026-02-01T08:00:00+00:00",
                    "end": "2026-02-01T09:00:00+00:00",
                }
            ]
        }
    )
    loader = PromptLoader("src/tv_list_aggregator/infrastructure/llm/prompts")
    parser = LLMParser(llm=_StubLLM(payload), prompts=loader)
    out = await parser.parse(b"<html>x</html>", hint={"source_id": "s2"})
    assert len(out) == 1 and out[0].title == "LLM"


@pytest.mark.asyncio
async def test_llm_parser_propagates_error() -> None:
    class _Boom:
        async def complete(self, prompt: str, *, json_mode: bool = False) -> str:
            raise LLMError("rate limit")

        async def embed(self, text: str) -> list[float]:
            return []

    loader = PromptLoader("src/tv_list_aggregator/infrastructure/llm/prompts")
    parser = LLMParser(llm=_Boom(), prompts=loader)
    with pytest.raises(ParseError):
        await parser.parse(b"x")
