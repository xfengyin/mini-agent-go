"""用户反馈服务（占位，预留接口）。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass
class Feedback:
    """用户对聚合结果的纠错反馈。"""

    program_identity_key: str
    field: str
    old_value: str
    new_value: str
    submitted_at: datetime


class FeedbackRepository(Protocol):
    """反馈仓储接口。"""

    async def add(self, fb: Feedback) -> None: ...
    async def list(self, identity_key: str | None = None, limit: int = 50) -> list[Feedback]: ...


class FeedbackService:
    """接收反馈并在后续聚合中应用。"""

    def __init__(self, repo: FeedbackRepository) -> None:
        self.repo = repo

    async def submit(
        self, identity_key: str, field: str, old: str, new: str
    ) -> Feedback:
        fb = Feedback(
            program_identity_key=identity_key,
            field=field,
            old_value=old,
            new_value=new,
            submitted_at=datetime.now(tz=UTC),
        )
        await self.repo.add(fb)
        return fb
