"""速率限制（slowapi）。"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from ....core.settings import get_settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{get_settings().rate_limit_per_minute}/minute"],
)
