"""Source 更新路由测试。"""
from __future__ import annotations

import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient


def _setup_env(db_path: str) -> None:
    """设置环境变量并清缓存。"""
    os.environ["TV_LIST_DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["TV_LIST_BOOTSTRAP_SCHEMA"] = "1"
    os.environ["TV_LIST_AUTO_SEED"] = "1"
    os.environ["TV_LIST_SECRET_KEY"] = "test-secret-1234567890"
    os.environ["TV_LIST_SEED_USERS"] = "admin:admin123:admin,user:user123:user"
    os.environ["TV_LIST_APP_ENV"] = "development"
    # 清 lru_cache 让 settings 重读 env
    from tv_list_aggregator.core.settings import reset_settings_cache
    reset_settings_cache()


@pytest.mark.asyncio
async def test_update_source_ok() -> None:
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
            # 1. 登录获取 admin token
            r = await c.post(
                "/api/v1/auth/token",
                data={"username": "admin", "password": "admin123"},
            )
            assert r.status_code == 200, r.text
            token = r.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 2. 更新源
            r = await c.put(
                "/api/v1/sources/src_demo_iqiyi",
                json={"name": "iQIYI 新名", "priority": 9},
                headers=headers,
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["name"] == "iQIYI 新名"
            assert body["priority"] == 9

    os.unlink(path)


@pytest.mark.asyncio
async def test_update_source_not_found() -> None:
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
            r = await c.post(
                "/api/v1/auth/token",
                data={"username": "admin", "password": "admin123"},
            )
            assert r.status_code == 200, r.text
            token = r.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            r = await c.put(
                "/api/v1/sources/missing-id-xyz",
                json={"name": "x"},
                headers=headers,
            )
            assert r.status_code == 404

    os.unlink(path)


@pytest.mark.asyncio
async def test_update_source_requires_admin() -> None:
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
            r = await c.post(
                "/api/v1/auth/token",
                data={"username": "user", "password": "user123"},
            )
            assert r.status_code == 200, r.text
            token = r.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            r = await c.put(
                "/api/v1/sources/src_demo_iqiyi",
                json={"name": "hack"},
                headers=headers,
            )
            assert r.status_code == 403

    os.unlink(path)
