"""去重服务单元测试。"""
from __future__ import annotations

from datetime import UTC, datetime

from tv_list_aggregator.domain.models.program import TVProgram
from tv_list_aggregator.domain.models.value_objects import Channel, Tag, TimeSlot
from tv_list_aggregator.domain.services.dedup_service import DedupService


def _p(sid: str = "a", title: str = "X") -> TVProgram:
    ch = Channel(id="c1", name="C1")
    slot = TimeSlot(
        start=datetime(2026, 1, 1, 10, tzinfo=UTC),
        end=datetime(2026, 1, 1, 11, tzinfo=UTC),
    )
    return TVProgram(
        title=title,
        channel=ch,
        slot=slot,
        source_ids=[sid],
        identity_key="k1",
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
        tags=[Tag(label="新闻", category="genre")],
    )


def test_dedup_merges_sources() -> None:
    out = DedupService().merge([_p("a"), _p("b")])
    assert len(out) == 1
    assert set(out[0].source_ids) == {"a", "b"}


def test_dedup_keeps_separate_identities() -> None:
    p1 = _p()
    p2 = _p()
    p2.identity_key = "k2"
    out = DedupService().merge([p1, p2])
    assert len(out) == 2


def test_dedup_merges_tags_unique() -> None:
    p1 = _p()
    p2 = _p()
    p2.tags = [Tag(label="新闻", category="genre"), Tag(label="大陆", category="region")]
    out = DedupService().merge([p1, p2])
    assert len(out) == 1
    assert {t.label for t in out[0].tags} == {"新闻", "大陆"}
