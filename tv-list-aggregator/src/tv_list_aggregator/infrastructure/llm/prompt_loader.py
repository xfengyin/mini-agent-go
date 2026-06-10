"""YAML 提示词模板加载器。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


class PromptLoader:
    """从 YAML 文件加载并渲染提示词模板（简单 {{ var }} 占位符）。"""

    def __init__(self, base_dir: str | Path) -> None:
        self.base = Path(base_dir)

    def load(self, name: str) -> dict[str, Any]:
        """加载模板原始 dict。"""
        path = self.base / f"{name}.yaml"
        with path.open(encoding="utf-8") as f:
            data: object = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}

    def render(self, name: str, **variables: object) -> str:
        """加载并使用 {{ var }} 占位符渲染。"""
        data = self.load(name)
        template: str = data.get("user_template", "")
        for k, v in variables.items():
            template = template.replace("{{ " + k + " }}", str(v))
        return template
