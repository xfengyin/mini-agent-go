"""通用类型别名。"""
from __future__ import annotations

from datetime import datetime
from typing import TypeAlias

# ISO8601 字符串或 datetime 对象
TimeLike: TypeAlias = datetime | str
# 任意 JSON 可序列化值
JSONValue: TypeAlias = str | int | float | bool | None | list | dict
