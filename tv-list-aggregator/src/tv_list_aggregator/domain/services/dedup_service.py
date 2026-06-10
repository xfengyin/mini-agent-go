"""去重服务：基于 identity_key 分组并合并 source_ids/description/tags。"""
from __future__ import annotations

from collections import defaultdict

from ..models.program import TVProgram
from ..models.value_objects import Tag


class DedupService:
    """按 identity_key 合并多源节目。"""

    def __init__(self, similarity_threshold: float = 0.85) -> None:
        self.threshold = similarity_threshold

    def merge(self, programs: list[TVProgram]) -> list[TVProgram]:
        groups: dict[str, list[TVProgram]] = defaultdict(list)
        for p in programs:
            groups[p.identity_key].append(p)
        merged: list[TVProgram] = []
        for items in groups.values():
            if len(items) == 1:
                merged.append(items[0])
                continue
            base = items[0].model_copy(deep=True)
            base.source_ids = sorted({sid for p in items for sid in p.source_ids})
            base.description = next(
                (p.description for p in items if p.description), base.description
            )
            # 合并去重 tags
            tag_set: dict[tuple[str, str], Tag] = {}
            for p in items:
                for t in p.tags:
                    tag_set[(t.label, t.category)] = t
            base.tags = list(tag_set.values())
            base.version = max(p.version for p in items)
            merged.append(base)
        return merged
