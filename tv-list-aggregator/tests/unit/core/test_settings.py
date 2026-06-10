"""Settings 与 logging 测试。"""
from __future__ import annotations


def test_settings_loads_from_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    from tv_list_aggregator.core.settings import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]
    s = get_settings()
    assert s.app_env == "test"
    assert s.database_url.startswith("sqlite")


def test_logging_configure_idempotent() -> None:
    from tv_list_aggregator.core.logging import configure_logging, get_logger

    configure_logging("DEBUG")
    log = get_logger("test")
    log.info("hello", foo="bar")  # 不抛异常即可
