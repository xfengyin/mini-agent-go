"""启动期 schema bootstrap 集成测试：dev 模式自动建表；prod 模式不建。"""
from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.fixture
async def temp_db_file() -> AsyncIterator[str]:
    """临时文件 SQLite，确保跨连接可共享 schema。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    url = f"sqlite+aiosqlite:///{path}"
    yield url
    with contextlib.suppress(FileNotFoundError):
        os.unlink(path)


def _has_sources_table(db_url: str) -> bool:
    """同步检查：给定 db url 里是否有 sources 表。"""
    import asyncio

    from sqlalchemy import text

    async def _check() -> bool:
        e = create_async_engine(db_url)
        try:
            async with e.connect() as conn:
                # 通过 PRAGMA 查 sqlite_master（不依赖表存在）
                rows = await conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='sources'")
                )
                return rows.first() is not None
        finally:
            await e.dispose()

    return asyncio.run(_check())


def test_lifespan_bootstrap_schema_in_dev(temp_db_file: str) -> None:
    """dev 模式启动 lifespan 应自动建表（TV_LIST_BOOTSTRAP_SCHEMA 默认 1）。"""
    os.environ["TV_LIST_DATABASE_URL"] = temp_db_file
    os.environ["TV_LIST_APP_ENV"] = "development"
    os.environ["TV_LIST_SECRET_KEY"] = "test-secret"  # noqa: S105
    os.environ.pop("TV_LIST_BOOTSTRAP_SCHEMA", None)
    from tv_list_aggregator.core.settings import reset_settings_cache
    from tv_list_aggregator.interfaces.api.deps import reset_deps

    reset_settings_cache()
    reset_deps()

    from tv_list_aggregator.interfaces.api.app import create_app

    app = create_app()
    with TestClient(app):
        # lifespan 跑完后应当建出 sources 表
        assert _has_sources_table(temp_db_file), "dev 模式 lifespan 应自动建表"


def test_lifespan_bootstrap_schema_in_production_disabled_by_default(temp_db_file: str) -> None:
    """prod 模式默认不自动建表。"""
    os.environ["TV_LIST_DATABASE_URL"] = temp_db_file
    os.environ["TV_LIST_APP_ENV"] = "production"
    os.environ["TV_LIST_SECRET_KEY"] = "test-secret-strong-enough"  # noqa: S105
    os.environ.pop("TV_LIST_BOOTSTRAP_SCHEMA", None)
    from tv_list_aggregator.core.settings import reset_settings_cache
    from tv_list_aggregator.interfaces.api.deps import reset_deps

    reset_settings_cache()
    reset_deps()

    from tv_list_aggregator.interfaces.api.app import create_app

    app = create_app()
    with TestClient(app):
        # prod 模式默认不 bootstrap
        assert not _has_sources_table(temp_db_file), "prod 模式默认不应自动建表"


def test_lifespan_bootstrap_schema_can_be_forced(temp_db_file: str) -> None:
    """TV_LIST_BOOTSTRAP_SCHEMA=1 在 prod 模式也强制建表。"""
    os.environ["TV_LIST_DATABASE_URL"] = temp_db_file
    os.environ["TV_LIST_APP_ENV"] = "production"
    os.environ["TV_LIST_SECRET_KEY"] = "test-secret-strong-enough"  # noqa: S105
    os.environ["TV_LIST_BOOTSTRAP_SCHEMA"] = "1"
    from tv_list_aggregator.core.settings import reset_settings_cache
    from tv_list_aggregator.interfaces.api.deps import reset_deps

    reset_settings_cache()
    reset_deps()

    from tv_list_aggregator.interfaces.api.app import create_app

    app = create_app()
    with TestClient(app):
        assert _has_sources_table(temp_db_file), "显式 TV_LIST_BOOTSTRAP_SCHEMA=1 应建表"
