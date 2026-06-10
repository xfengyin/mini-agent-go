"""端到端冒烟测试：fetcher→parser→dedup。"""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from tv_list_aggregator.domain.services.dedup_service import DedupService
from tv_list_aggregator.infrastructure.http.client import ResilientHTTPFetcher
from tv_list_aggregator.plugins.parsers.json_parser import JSONParser


@pytest.mark.asyncio
async def test_end_to_end_json_pipeline() -> None:
    body = json.dumps(
        [
            {
                "title": "  A ",
                "channel": "C1",
                "start": "2026-01-01T10:00:00+00:00",
                "end": "2026-01-01T11:00:00+00:00",
            },
            {
                "title": "A",
                "channel": "C1",
                "start": "2026-01-01T10:00:00+00:00",
                "end": "2026-01-01T11:00:00+00:00",
            },
        ]
    ).encode()

    fetcher = ResilientHTTPFetcher(rate_per_minute=10000)
    with respx.mock(base_url="https://e") as mock:
        mock.get("/p").mock(return_value=httpx.Response(200, content=body))
        r = await fetcher.fetch("https://e/p")
        programs = await JSONParser().parse(r.body, hint={"source_id": "s1"})
        # 两条同 identity_key，去重后剩 1
        merged = DedupService().merge(programs)
        assert len(merged) == 1
        assert merged[0].title.strip() == "A"
    await fetcher.aclose()
