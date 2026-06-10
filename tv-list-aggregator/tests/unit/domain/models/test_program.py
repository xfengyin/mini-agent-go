"""Program/Source 实体测试。"""
from __future__ import annotations

from datetime import UTC, datetime

from tv_list_aggregator.domain.models.program import TVProgram
from tv_list_aggregator.domain.models.source import SourceStatus, SourceType
from tv_list_aggregator.domain.models.value_objects import Channel, TimeSlot


def test_program_construction() -> None:
    p = TVProgram(
        title="新闻联播",
        channel=Channel(id="cctv1", name="CCTV-1"),
        slot=TimeSlot(
            start=datetime(2026, 1, 1, 19, tzinfo=UTC),
            end=datetime(2026, 1, 1, 19, 30, tzinfo=UTC),
        ),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        identity_key="abc",
    )
    assert p.title == "新闻联播"
    assert p.channel.id == "cctv1"


def test_source_status_enum() -> None:
    assert SourceStatus.ACTIVE.value == "active"
    assert SourceType.HTTP_JSON.value == "http_json"


def test_value_objects_are_frozen() -> None:
    from pydantic import ValidationError

    ch = Channel(id="c1", name="C1")
    try:
        ch.id = "c2"  # type: ignore[misc]
    except ValidationError:
        pass
    # pydantic v2 frozen 模型对赋值行为是 raise
    assert ch.id == "c1"
