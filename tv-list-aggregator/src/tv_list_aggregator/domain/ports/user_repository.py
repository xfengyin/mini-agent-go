"""User Repository 端口：抽象 User 持久化与认证。"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models.user import User


@runtime_checkable
class UserRepository(Protocol):
    """User 仓储抽象。"""

    async def get_by_username(self, username: str) -> tuple[User, str] | None:
        """返回 (User, password_hash)，未找到返回 None。"""
        ...

    async def get_by_id(self, user_id: str) -> User | None:
        """按 id 查找。"""
        ...

    async def add(self, user: User, password_hash: str) -> None:
        """插入新用户。"""
        ...

    async def list_all(self) -> list[User]:
        """列出全部用户（管理用）。"""
        ...
