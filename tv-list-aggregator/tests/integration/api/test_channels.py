"""频道聚合路由测试。"""
from __future__ import annotations

import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient


def _setup_env(db_path: str) -> None:
    os.environ["TV_LIST_DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["TV_LIST_BOOTSTRAP_SCHEMA"] = "1"
    os.environ["TV_LIST_AUTO_SEED"] = "1"
    os.environ["TV_LIST_SECRET_KEY"] = "test-secret-1234567890"
    os.environ["TV_LIST_SEED_USERS"] = "admin:admin123:admin"
    os.environ["TV_LIST_APP_ENV"] = "development"
    from tv_list_aggregator.core.settings import reset_settings_cache
    reset_settings_cache()


@pytest.mark.asyncio
async def test_list_channels_ok() -> None:
    from tv_list_aggregator.interfaces.api.app import create_app
    from tv_list_aggregator.interfaces.api.deps import reset_deps

    reset_deps()
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    _setup_env(path)

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        async with app.router.lifespan_context(app):
            r = await c.get("/api/v1/channels")
            assert r.status_code == 200, r.text
            data = r.json()
            assert isinstance(data, list)
            assert len(data) > 0, "expected at least one channel from seed"
            assert "channel_id" in data[0]
            assert "channel_name" in data[0]
            assert "program_count" in data[0]
            # 节目数应该 >= 1
            assert data[0]["program_count"] >= 1
            # 按降序
            counts = [c["program_count"] for c in data]
            assert counts == sorted(counts, reverse=True)

    os.unlink(path)
