"""数据导出路由（CSV）。"""
from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from ....infrastructure.persistence.program_repository_impl import (
    SQLAlchemyProgramRepository,
)
from ..deps import get_program_repo

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/programs.csv")
async def export_programs_csv(
    start: datetime = Query(...),
    end: datetime = Query(...),
    channel_id: str | None = None,
    repo: SQLAlchemyProgramRepository = Depends(get_program_repo),
) -> StreamingResponse:
    rows = await repo.list_by_range(start, end, channel_id=channel_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["title", "channel", "start", "end", "description"])
    for p in rows:
        writer.writerow(
            [
                p.title,
                p.channel.name,
                p.slot.start.isoformat(),
                p.slot.end.isoformat(),
                p.description or "",
            ]
        )
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv")
