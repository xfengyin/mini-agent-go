"""领域异常层级。

按可重试性区分 TransientError / PermanentError，
便于调度器、重试中间件、API 错误处理统一决策。
"""
from __future__ import annotations


class TVListBaseError(Exception):
    """所有领域异常的基类。"""


class TransientError(TVListBaseError):
    """可重试的瞬时错误（网络抖动、限流、服务暂时不可用）。"""


class PermanentError(TVListBaseError):
    """不可重试的永久错误（4xx、解析失败、字段缺失）。"""


class SourceUnavailableError(TransientError):
    """数据源不可用（连接失败、5xx）。"""


class SourceAuthError(PermanentError):
    """鉴权失败（401/403）。"""


class ParseError(PermanentError):
    """解析失败。"""


class RateLimitError(TransientError):
    """触发限流（429）。"""


class StorageError(TVListBaseError):
    """存储层错误。"""


class LLMError(TVListBaseError):
    """LLM 调用失败。"""


class ConfigurationError(TVListBaseError):
    """配置错误。"""
