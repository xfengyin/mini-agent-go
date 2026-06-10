"""FastAPI 依赖注入：Session / Repository。"""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
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


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def get_source_repo(session: AsyncSession = Depends(get_session)):
    return SQLAlchemySourceRepository(session)


async def get_program_repo(session: AsyncSession = Depends(get_session)):
    return SQLAlchemyProgramRepository(session)


async def get_job_repo(session: AsyncSession = Depends(get_session)):
    return SQLAlchemyJobRepository(session)
