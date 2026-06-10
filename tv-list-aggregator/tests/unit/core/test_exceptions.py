"""领域异常层级测试。"""
from __future__ import annotations

from tv_list_aggregator.core.exceptions import (
    LLMError,
    PermanentError,
    RateLimitError,
    SourceAuthError,
    SourceUnavailableError,
    StorageError,
    TransientError,
    TVListBaseError,
)


def test_all_inherit_base() -> None:
    for cls in (TransientError, PermanentError, LLMError, StorageError):
        assert issubclass(cls, TVListBaseError)


def test_rate_limit_is_transient() -> None:
    assert issubclass(RateLimitError, TransientError)


def test_source_unavailable_is_transient() -> None:
    assert issubclass(SourceUnavailableError, TransientError)


def test_source_auth_is_permanent() -> None:
    assert issubclass(SourceAuthError, PermanentError)
    assert not issubclass(SourceAuthError, TransientError)
