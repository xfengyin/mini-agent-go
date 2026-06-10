"""数据源管理路由。"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status

from ....domain.models.source import SourceStatus, TVListSource
from ....infrastructure.persistence.source_repository_impl import (
    SQLAlchemySourceRepository,
)
from ..deps import get_source_repo
from ..schemas.source import SourceCreate, SourceOut
from ..security import ROLE_ADMIN, require_role

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post(
    "",
    response_model=SourceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def create_source(
    payload: SourceCreate,
    repo: SQLAlchemySourceRepository = Depends(get_source_repo),
):
    now = datetime.now(tz=UTC)
    src = TVListSource(
        id=str(uuid.uuid4()),
        **payload.model_dump(),
        status=SourceStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    await repo.add(src)
    return src


@router.get("", response_model=list[SourceOut])
async def list_sources(
    repo: SQLAlchemySourceRepository = Depends(get_source_repo),
):
    return await repo.list()


@router.get("/{source_id}", response_model=SourceOut)
async def get_source(
    source_id: str,
    repo: SQLAlchemySourceRepository = Depends(get_source_repo),
):
    s = await repo.get(source_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "source not found")
    return s


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def delete_source(
    source_id: str,
    repo: SQLAlchemySourceRepository = Depends(get_source_repo),
):
    await repo.delete(source_id)
    return


@router.post(
    "/{source_id}/enable",
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def enable_source(
    source_id: str,
    repo: SQLAlchemySourceRepository = Depends(get_source_repo),
):
    s = await repo.get(source_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "source not found")
    s.status = SourceStatus.ACTIVE
    await repo.update(s)
    return {"ok": True}


@router.post(
    "/{source_id}/disable",
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def disable_source(
    source_id: str,
    repo: SQLAlchemySourceRepository = Depends(get_source_repo),
):
    s = await repo.get(source_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "source not found")
    s.status = SourceStatus.DISABLED
    await repo.update(s)
    return {"ok": True}
