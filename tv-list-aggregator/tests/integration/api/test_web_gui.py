"""Web GUI + dashboard 集成测试。"""
from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
async def temp_db_file() -> AsyncIterator[str]:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    url = f"sqlite+aiosqlite:///{path}"
    yield url
    with contextlib.suppress(FileNotFoundError):
        os.unlink(path)


def _build_test_client(db_url: str) -> TestClient:
    """装配测试用 FastAPI client（启用 schema bootstrap）。"""
    os.environ["TV_LIST_DATABASE_URL"] = db_url
    os.environ["TV_LIST_APP_ENV"] = "development"
    os.environ["TV_LIST_SECRET_KEY"] = "test-secret"  # noqa: S105
    os.environ["TV_LIST_BOOTSTRAP_SCHEMA"] = "1"
    from tv_list_aggregator.core.settings import reset_settings_cache
    from tv_list_aggregator.interfaces.api.deps import reset_deps

    reset_settings_cache()
    reset_deps()

    from tv_list_aggregator.interfaces.api.app import create_app

    app = create_app()
    return TestClient(app)


def test_root_serves_index_html(temp_db_file: str) -> None:
    """GET / 应返回 HTML 入口页。"""
    with _build_test_client(temp_db_file) as c:
        r = c.get("/")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/html")
        assert "<title>TVLIST" in r.text
        # 关键 DOM 节点必须存在
        for marker in (
            'id="epgBody"',
            'id="programGrid"',
            'id="sourceList"',
            'id="jobTable"',
            'id="rankList"',
            "/static/style.css",
            "/static/app.js",
        ):
            assert marker in r.text, f"GUI 必须包含 {marker}"


def test_static_files_are_served(temp_db_file: str) -> None:
    """静态资源 200。"""
    with _build_test_client(temp_db_file) as c:
        r = c.get("/static/style.css")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/css")
        assert "fraunces" in r.text.lower() or "JetBrains" in r.text

        r = c.get("/static/app.js")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith(("application/javascript", "text/javascript"))
        assert "switchView" in r.text


def test_dashboard_summary_endpoint(temp_db_file: str) -> None:
    """dashboard/summary 返回基本结构。"""
    with _build_test_client(temp_db_file) as c:
        r = c.get("/api/v1/dashboard/summary")
        assert r.status_code == 200
        body = r.json()
        assert "generated_at" in body
        assert "programs" in body and "total" in body["programs"]
        assert "sources" in body
        assert "jobs" in body
        assert "by_status" in body["jobs"]


def test_dashboard_timeline_endpoint(temp_db_file: str) -> None:
    """dashboard/timeline 返回时间轴数据。"""
    with _build_test_client(temp_db_file) as c:
        r = c.get("/api/v1/dashboard/timeline?hours=3")
        assert r.status_code == 200
        body = r.json()
        assert "from" in body and "to" in body and "now" in body
        assert "programs_by_channel" in body
        assert isinstance(body["programs_by_channel"], dict)


def test_dashboard_top_channels_endpoint(temp_db_file: str) -> None:
    """dashboard/top-channels 返回 Top N。"""
    with _build_test_client(temp_db_file) as c:
        r = c.get("/api/v1/dashboard/top-channels?limit=5")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert isinstance(body["items"], list)
