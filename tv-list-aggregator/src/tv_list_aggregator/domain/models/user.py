"""User 聚合根：username/password/role。"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["admin", "user"]


class User(BaseModel):
    """最小可用 User 实体（密码哈希外置）。"""

    model_config = {"frozen": False}

    id: str
    username: str = Field(min_length=1, max_length=64)
    role: Role = "user"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    disabled: bool = False
