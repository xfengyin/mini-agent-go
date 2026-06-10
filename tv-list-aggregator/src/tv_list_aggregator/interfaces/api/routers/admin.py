"""管理员路由：手动触发抓取、查看插件清单、种子数据。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.settings import get_settings
from ....infrastructure.persistence.source_repository_impl import (
    SQLAlchemySourceRepository,
)
from ....plugins.registry import PluginRegistry
from ..deps import get_session, get_source_repo

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/plugins")
async def list_plugins(request: Request) -> dict[str, Any]:
    registry: PluginRegistry | None = getattr(request.app.state, "registry", None)
    if registry is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "registry not initialized")
    return {
        "source_types": registry.list_source_types(),
        "parsers": registry.list_parsers(),
    }


@router.post("/crawl/{source_id}")
async def trigger_crawl(
    source_id: str,
    request: Request,
    repo: SQLAlchemySourceRepository = Depends(get_source_repo),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    agg = getattr(request.app.state, "agg", None)
    if agg is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "aggregator not initialized")
    src = await repo.get(source_id)
    if not src:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "source not found")
    job = await agg.run_once(src)
    await session.commit()
    return {"ok": True, "job_id": job.id, "status": job.status.value}


@router.post("/crawl-all")
async def trigger_crawl_all(
    request: Request,
    repo: SQLAlchemySourceRepository = Depends(get_source_repo),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """触发所有 active 源的抓取。返回每个源对应的 job_id 或 error。"""
    agg = getattr(request.app.state, "agg", None)
    if agg is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "aggregator not initialized")
    sources = await repo.list(status="active")
    results: list[dict[str, Any]] = []
    for src in sources:
        try:
            job = await agg.run_once(src)
            results.append(
                {
                    "source_id": src.id,
                    "ok": True,
                    "job_id": job.id,
                    "status": job.status.value,
                }
            )
        except Exception as e:  # noqa: BLE001
            results.append({"source_id": src.id, "ok": False, "error": str(e)})
    await session.commit()
    return {"total": len(sources), "results": results}


@router.post("/seed")
async def seed_data(request: Request) -> dict[str, Any]:
    """开发期：把示例数据写入数据库（生产环境拒绝执行）。"""
    s = get_settings()
    if s.is_production():
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "seed endpoint disabled in production"
        )
    from ..seed import seed_if_empty

    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "session_factory not initialized")
    return await seed_if_empty(session_factory)


@router.post("/reseed")
async def reseed_data(request: Request) -> dict[str, Any]:
    """开发期：清空并重新写入示例数据。"""
    s = get_settings()
    if s.is_production():
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "reseed endpoint disabled in production"
        )
    from ..seed import reset_and_seed

    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "session_factory not initialized")
    return await reset_and_seed(session_factory)
