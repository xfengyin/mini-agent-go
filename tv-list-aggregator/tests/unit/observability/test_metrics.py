"""业务指标测试。"""
from __future__ import annotations

from tv_list_aggregator.observability.metrics import (
    ACTIVE_SOURCES,
    CRAWL_FAILURE,
    CRAWL_SUCCESS,
    PROGRAMS_INGESTED,
)


def test_counter_increments() -> None:
    CRAWL_SUCCESS.labels(source_id="x").inc()
    CRAWL_FAILURE.labels(source_id="x", reason="timeout").inc()
    PROGRAMS_INGESTED.inc()
    ACTIVE_SOURCES.set(3)
    assert ACTIVE_SOURCES._value.get() == 3  # type: ignore[attr-defined]
