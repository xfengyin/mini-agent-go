"""FastAPI 依赖注入：Session / Repository。

优先从 app.state 读取 engine/session_factory（lifespan 注入），
否则回退到懒加载 settings.database_url（兼容 tests 与脚本场景）。
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ...core.settings import get_settings
from ...infrastructure.persistence.job_repository_impl import SQLAlchemyJobRepository
from ...infrastructure.persistence.program_repository_impl import (
    SQLAlchemyProgramRepository,
)
from ...infrastructure.persistence.source_repository_impl import (
    SQLAlchemySourceRepository,
)

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_or_create_engine():
    """尝试从 app.state 读 engine，否则懒加载 settings。"""
    global _engine
    if _engine is not None:
        return _engine
    _engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


def _get_or_create_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is not None:
        return _session_factory
    _session_factory = async_sessionmaker(
        _get_or_create_engine(), expire_on_commit=False, class_=AsyncSession
    )
    return _session_factory


def reset_deps() -> None:
    """测试用：清空模块级缓存。"""
    global _engine, _session_factory
    _engine = None
    _session_factory = None


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """每次请求返回一个 session。优先用 lifespan 注入的 session_factory。"""
    sf = getattr(request.app.state, "session_factory", None) or _get_or_create_session_factory()
    async with sf() as session:
        yield session


async def get_source_repo(session: AsyncSession = Depends(get_session)):
    return SQLAlchemySourceRepository(session)


async def get_program_repo(session: AsyncSession = Depends(get_session)):
    return SQLAlchemyProgramRepository(session)


async def get_job_repo(session: AsyncSession = Depends(get_session)):
    return SQLAlchemyJobRepository(session)
