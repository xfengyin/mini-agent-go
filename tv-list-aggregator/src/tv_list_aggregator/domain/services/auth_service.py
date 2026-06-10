"""User 认证服务：bcrypt 校验、token 签发。"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from passlib.context import CryptContext  # type: ignore[import-untyped]

from ...core.logging import get_logger
from ...core.settings import get_settings
from ...infrastructure.persistence.user_repository_impl import SQLAlchemyUserRepository
from ..models.user import User

log = get_logger(__name__)
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")  # type: ignore[call-arg]


def hash_password(plain: str) -> str:
    """bcrypt 哈希。"""
    return _pwd.hash(plain)  # type: ignore[no-any-return]


def verify_password(plain: str, hashed: str) -> bool:
    """bcrypt 校验。"""
    try:
        return bool(_pwd.verify(plain, hashed))
    except Exception:
        return False


def seed_default_admin() -> None:
    """根据 TV_LIST_SEED_USERS 配置创建/更新种子用户。

    格式：admin1:plaintext1:admin,user1:plaintext1:user
    仅在 dev 环境且用户不存在时执行。
    """
    s = get_settings()
    if s.is_production() or not s.seed_users:
        return
    # 占位：实际写入由 lifespan 通过 session 调用
    log.info("seed_users.configured", count=len([p for p in s.seed_users.split(",") if p]))


class AuthService:
    """使用 UserRepository 实现的认证服务。"""

    def __init__(self, user_repo: SQLAlchemyUserRepository) -> None:
        self.repo = user_repo

    async def authenticate(self, username: str, password: str) -> User | None:
        """校验用户名密码，返回 User 或 None。"""
        record = await self.repo.get_by_username(username)
        if record is None:
            return None
        user, password_hash = record
        if user.disabled:
            return None
        if not verify_password(password, password_hash):
            return None
        return user

    async def create_user(self, username: str, password: str, role: str = "user") -> User:
        """创建新用户。"""
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            role=role,
            created_at=datetime.now(UTC),
            disabled=False,
        )
        await self.repo.add(user, hash_password(password))
        return user
