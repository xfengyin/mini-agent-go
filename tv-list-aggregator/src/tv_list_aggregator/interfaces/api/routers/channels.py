"""频道聚合路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....infrastructure.persistence.models import ProgramRow
from ..deps import get_session
from ..schemas.channel import ChannelOut

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("", response_model=list[ChannelOut])
async def list_channels(session: AsyncSession = Depends(get_session)) -> list[ChannelOut]:
    """返回所有不重复频道，按节目数降序。"""
    stmt = (
        select(
            ProgramRow.channel_id,
            ProgramRow.channel_name,
            ProgramRow.channel_country,
            ProgramRow.channel_language,
            func.count(ProgramRow.id).label("program_count"),
        )
        .group_by(
            ProgramRow.channel_id,
            ProgramRow.channel_name,
            ProgramRow.channel_country,
            ProgramRow.channel_language,
        )
        .order_by(func.count(ProgramRow.id).desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        ChannelOut(
            channel_id=r.channel_id,
            channel_name=r.channel_name,
            channel_country=r.channel_country,
            channel_language=r.channel_language,
            program_count=int(r.program_count),
        )
        for r in rows
    ]
