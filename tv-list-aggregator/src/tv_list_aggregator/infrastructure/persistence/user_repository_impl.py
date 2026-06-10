"""User 仓储 SQLAlchemy 实现（UserRow 表）。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.models.user import User
from ...domain.ports.user_repository import UserRepository
from .models import UserRow


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_username(self, username: str) -> tuple[User, str] | None:
        stmt = select(UserRow).where(UserRow.username == username)
        res = (await self.session.execute(stmt)).scalar_one_or_none()
        if res is None:
            return None
        return self._to_domain(res), res.password_hash

    async def get_by_id(self, user_id: str) -> User | None:
        res = await self.session.get(UserRow, user_id)
        return self._to_domain(res) if res else None

    async def add(self, user: User, password_hash: str) -> None:
        self.session.add(
            UserRow(
                id=user.id,
                username=user.username,
                password_hash=password_hash,
                role=user.role,
                created_at=user.created_at,
                disabled=user.disabled,
            )
        )

    async def list_all(self) -> list[User]:
        stmt = select(UserRow).order_by(UserRow.created_at)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    @staticmethod
    def _to_domain(row: UserRow) -> User:
        return User(
            id=row.id,
            username=row.username,
            role=row.role,  # type: ignore[arg-type]
            created_at=row.created_at,
            disabled=row.disabled,
        )
