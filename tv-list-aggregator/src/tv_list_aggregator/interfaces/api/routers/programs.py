"""节目查询路由。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from ....infrastructure.persistence.program_repository_impl import (
    SQLAlchemyProgramRepository,
)
from ..deps import get_program_repo
from ..schemas.program import ProgramOut

router = APIRouter(prefix="/programs", tags=["programs"])


@router.get("", response_model=list[ProgramOut])
async def list_programs(
    start: datetime = Query(...),
    end: datetime = Query(...),
    channel_id: str | None = None,
    repo: SQLAlchemyProgramRepository = Depends(get_program_repo),
) -> list[ProgramOut]:
    rows = await repo.list_by_range(start, end, channel_id=channel_id)
    out: list[ProgramOut] = []
    for p in rows:
        out.append(
            ProgramOut(
                id=p.id,
                title=p.title,
                description=p.description,
                channel_id=p.channel.id,
                channel_name=p.channel.name,
                start=p.slot.start,
                end=p.slot.end,
                timezone=p.slot.timezone,
                tags=[t.model_dump() for t in p.tags],
                source_ids=p.source_ids,
                version=p.version,
            )
        )
    return out


@router.get("/count")
async def count_programs(
    repo: SQLAlchemyProgramRepository = Depends(get_program_repo),
) -> dict[str, int]:
    return {"count": await repo.count()}
