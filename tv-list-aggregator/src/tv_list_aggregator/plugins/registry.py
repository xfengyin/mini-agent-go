"""插件注册器：按 type 动态查找源/解析器。"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .sources.base import SourceAdapter


class PluginRegistry:
    """源/解析器插件注册表（SPI 模式）。"""

    def __init__(self) -> None:
        self._sources: dict[str, Callable[[], SourceAdapter]] = {}
        self._parsers: dict[str, Any] = {}

    def register_source(self, type_name: str, factory: Callable[[], SourceAdapter]) -> None:
        self._sources[type_name] = factory

    def register_parser(self, name: str, parser: Any) -> None:
        self._parsers[name] = parser

    def build_source(self, type_name: str) -> SourceAdapter:
        if type_name not in self._sources:
            raise KeyError(f"unknown source type: {type_name}")
        return self._sources[type_name]()

    def get_parser(self, name: str) -> Any:
        if name not in self._parsers:
            raise KeyError(f"unknown parser: {name}")
        return self._parsers[name]

    def list_source_types(self) -> list[str]:
        return sorted(self._sources)

    def list_parsers(self) -> list[str]:
        return sorted(self._parsers)
