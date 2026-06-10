"""管理员路由：手动触发抓取、查看插件清单。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from ....plugins.registry import PluginRegistry

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/plugins")
async def list_plugins(request: Request) -> dict:
    registry: PluginRegistry | None = getattr(request.app.state, "registry", None)
    if registry is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "registry not initialized")
    return {
        "source_types": registry.list_source_types(),
        "parsers": registry.list_parsers(),
    }


@router.post("/crawl/{source_id}")
async def trigger_crawl(source_id: str, request: Request) -> dict:
    agg = getattr(request.app.state, "agg", None)
    registry: PluginRegistry | None = getattr(request.app.state, "registry", None)
    repo = getattr(request.app.state, "source_repo", None)
    if agg is None or repo is None or registry is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "app not initialized")
    src = await repo.get(source_id)
    if not src:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "source not found")
    job = await agg.run_once(src)
    return {"ok": True, "job_id": job.id, "status": job.status.value}
