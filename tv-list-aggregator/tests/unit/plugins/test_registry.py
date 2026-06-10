"""插件注册器测试。"""
from __future__ import annotations

import pytest

from tv_list_aggregator.plugins.registry import PluginRegistry
from tv_list_aggregator.plugins.sources.http_json_source import HTTPSource


def test_registry_register_and_build() -> None:
    reg = PluginRegistry()
    reg.register_source("http_json", lambda: HTTPSource(fetcher=None, parser=None))  # type: ignore[arg-type]
    assert reg.build_source("http_json").type == "http_json"
    assert "http_json" in reg.list_source_types()


def test_registry_unknown_type() -> None:
    reg = PluginRegistry()
    with pytest.raises(KeyError):
        reg.build_source("nope")
