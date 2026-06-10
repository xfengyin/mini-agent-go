"""数据源管理路由。"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.models.source import SourceStatus, TVListSource
from ....infrastructure.persistence.source_repository_impl import (
    SQLAlchemySourceRepository,
)
from ..deps import get_session, get_source_repo
from ..middleware.rate_limit import limiter
from ..schemas.source import SourceCreate, SourceOut, SourceUpdate
from ..security import ROLE_ADMIN, require_role

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post(
    "",
    response_model=SourceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
@limiter.limit("20/minute")
async def create_source(
    request: Request,
    payload: SourceCreate,
    repo: SQLAlchemySourceRepository = Depends(get_source_repo),
    session: AsyncSession = Depends(get_session),
) -> TVListSource:
    now = datetime.now(tz=UTC)
    data = payload.model_dump(exclude_none=False)
    src_id = data.pop("id") or str(uuid.uuid4())
    src = TVListSource(
        id=src_id,
        **data,
        status=SourceStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    await repo.add(src)
    await session.commit()
    return src


@router.get("", response_model=list[SourceOut])
async def list_sources(
    repo: SQLAlchemySourceRepository = Depends(get_source_repo),
) -> list[TVListSource]:
    return await repo.list()


@router.get("/{source_id}", response_model=SourceOut)
async def get_source(
    source_id: str,
    repo: SQLAlchemySourceRepository = Depends(get_source_repo),
) -> TVListSource:
    s = await repo.get(source_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "source not found")
    return s


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
@limiter.limit("20/minute")
async def delete_source(
    request: Request,
    source_id: str,
    repo: SQLAlchemySourceRepository = Depends(get_source_repo),
    session: AsyncSession = Depends(get_session),
) -> None:
    await repo.delete(source_id)
    await session.commit()
    return


@router.post(
    "/{source_id}/enable",
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
@limiter.limit("20/minute")
async def enable_source(
    request: Request,
    source_id: str,
    repo: SQLAlchemySourceRepository = Depends(get_source_repo),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    s = await repo.get(source_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "source not found")
    s.status = SourceStatus.ACTIVE
    await repo.update(s)
    await session.commit()
    return {"ok": True}


@router.post(
    "/{source_id}/disable",
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
@limiter.limit("20/minute")
async def disable_source(
    request: Request,
    source_id: str,
    repo: SQLAlchemySourceRepository = Depends(get_source_repo),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    s = await repo.get(source_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "source not found")
    s.status = SourceStatus.DISABLED
    await repo.update(s)
    await session.commit()
    return {"ok": True}


@router.put(
    "/{source_id}",
    response_model=SourceOut,
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
@limiter.limit("20/minute")
async def update_source(
    request: Request,
    source_id: str,
    payload: SourceUpdate,
    repo: SQLAlchemySourceRepository = Depends(get_source_repo),
    session: AsyncSession = Depends(get_session),
) -> TVListSource:
    """更新源配置（部分字段）。需 admin 权限。

    只更新 payload 中显式提供的字段（exclude_unset 语义），
    其余字段保持原值不变。
    """
    s = await repo.get(source_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "source not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if hasattr(s, k):
            setattr(s, k, v)
    s.updated_at = datetime.now(tz=UTC)
    await repo.update(s)
    await session.commit()
    return s
