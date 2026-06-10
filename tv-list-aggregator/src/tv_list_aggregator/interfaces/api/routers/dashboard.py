"""Dashboard 聚合接口：给 Web GUI 提供一次性快照数据。"""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....infrastructure.persistence.job_repository_impl import SQLAlchemyJobRepository
from ....infrastructure.persistence.models import ProgramRow
from ....infrastructure.persistence.program_repository_impl import (
    SQLAlchemyProgramRepository,
)
from ....infrastructure.persistence.source_repository_impl import (
    SQLAlchemySourceRepository,
)
from ..deps import get_job_repo, get_program_repo, get_session, get_source_repo

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(
    session: AsyncSession = Depends(get_session),
    src_repo: SQLAlchemySourceRepository = Depends(get_source_repo),
    prog_repo: SQLAlchemyProgramRepository = Depends(get_program_repo),
    job_repo: SQLAlchemyJobRepository = Depends(get_job_repo),
) -> dict:
    """聚合给 GUI 用的整体快照：节目数 / 源数 / 任务数 / 健康度。"""
    # 节目总数 + 24h 内节目数
    now = datetime.now(tz=UTC)
    cutoff = now - timedelta(hours=24)
    total_programs = await prog_repo.count()
    recent_programs_q = select(func.count(ProgramRow.id)).where(ProgramRow.start_at >= cutoff)
    recent_programs = (await session.execute(recent_programs_q)).scalar() or 0

    # 源统计
    sources = await src_repo.list()
    sources_total = len(sources)
    sources_by_status = Counter(s.status for s in sources)
    sources_by_type = Counter(s.type.value for s in sources)

    # 最近任务
    recent_jobs = await job_repo.list(limit=10)
    jobs_by_status = Counter(j.status.value for j in recent_jobs)

    return {
        "generated_at": now.isoformat(),
        "programs": {
            "total": total_programs,
            "last_24h": int(recent_programs),
        },
        "sources": {
            "total": sources_total,
            "active": sources_by_status.get("active", 0),
            "disabled": sources_by_status.get("disabled", 0),
            "by_type": dict(sources_by_type),
        },
        "jobs": {
            "recent": [
                {
                    "id": j.id,
                    "source_id": j.source_id,
                    "status": j.status.value,
                    "started_at": j.started_at.isoformat() if j.started_at else None,
                    "finished_at": j.finished_at.isoformat() if j.finished_at else None,
                    "items_fetched": j.items_fetched,
                    "items_saved": j.items_saved,
                }
                for j in recent_jobs
            ],
            "by_status": dict(jobs_by_status),
        },
    }


@router.get("/timeline")
async def dashboard_timeline(
    hours: int = 6,
    channel: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """EPG 时间轴数据：返回 N 小时内每个频道的节目块。

    给 GUI 横向时间轴用。
    """
    now = datetime.now(tz=UTC)
    start = now - timedelta(minutes=30)
    end = now + timedelta(hours=hours)
    stmt = (
        select(ProgramRow)
        .where(ProgramRow.start_at <= end, ProgramRow.end_at >= start)
        .order_by(ProgramRow.channel_id, ProgramRow.start_at)
    )
    if channel:
        stmt = stmt.where(ProgramRow.channel_id == channel)
    rows = (await session.execute(stmt)).scalars().all()

    # 按频道分组
    by_channel: dict[str, list[dict]] = {}
    for r in rows:
        by_channel.setdefault(r.channel_name, []).append(
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "start": r.start_at.isoformat(),
                "end": r.end_at.isoformat(),
                "channel_id": r.channel_id,
                "channel_name": r.channel_name,
                "tags": r.tags or [],
            }
        )
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "now": now.isoformat(),
        "channels": [
            {"id": r.channel_id, "name": r.channel_name}
            for r in rows[:1]  # placeholder, real list below
        ],
        "programs_by_channel": by_channel,
    }


@router.get("/top-channels")
async def top_channels(limit: int = 10, session: AsyncSession = Depends(get_session)) -> dict:
    """节目数 Top N 频道。"""
    stmt = (
        select(
            ProgramRow.channel_id,
            ProgramRow.channel_name,
            func.count(ProgramRow.id).label("cnt"),
        )
        .group_by(ProgramRow.channel_id, ProgramRow.channel_name)
        .order_by(func.count(ProgramRow.id).desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return {
        "items": [
            {
                "channel_id": r.channel_id,
                "channel_name": r.channel_name,
                "program_count": int(r.cnt),
            }
            for r in rows
        ]
    }
