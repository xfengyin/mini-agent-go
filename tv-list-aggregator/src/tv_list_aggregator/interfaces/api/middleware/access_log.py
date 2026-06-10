"""结构化访问日志中间件。

记录每个 HTTP 请求的关键指标：方法、路径、状态码、耗时、trace_id、用户 ID。
- 慢请求（> 500ms）以 warning 级别记录，便于告警/排查
- 异常也会以 error 级别记录，并重新抛出（不吞错）
- 依赖 ``RequestIDMiddleware`` 注入的 ``request.state.request_id`` 作为 trace_id
- 同步上报 HTTP 指标（请求计数、延迟直方图、活跃连接数）
"""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ....core.logging import get_logger
from ..routers.metrics import dec_inprogress, inc_inprogress, observe_http_request

# 慢请求阈值（毫秒），与 SRE 通用告警阈值对齐
SLOW_REQUEST_THRESHOLD_MS: float = 500.0

log = get_logger(__name__)


class AccessLogMiddleware(BaseHTTPMiddleware):
    """记录结构化访问日志（含慢请求告警）+ HTTP 指标打点。"""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # 起始时间戳（高精度）
        start: float = time.perf_counter()
        # 透传 trace_id：优先取 RequestIDMiddleware 注入的 request_id
        trace_id: str = getattr(request.state, "request_id", None) or "-"
        # 用户标识：未鉴权时为 None（结构化日志序列化为 null）
        user_id: str | None = getattr(request.state, "user_id", None)

        # 活跃连接（in-progress）指标 +1
        inc_inprogress()

        status_code: int = 500
        try:
            response = await call_next(request)
        except Exception as exc:  # noqa: BLE001
            # 计算耗时并以 error 级别记录（异常路径）
            duration_ms: float = (time.perf_counter() - start) * 1000.0
            log.error(
                "http.access",
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=round(duration_ms, 2),
                trace_id=trace_id,
                user_id=user_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            # 异常时仍上报指标（5xx），保持 inc/dec 配对
            observe_http_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_seconds=duration_ms / 1000.0,
            )
            dec_inprogress()
            raise

        status_code = response.status_code
        duration_ms = (time.perf_counter() - start) * 1000.0
        # 上报 HTTP 指标
        observe_http_request(
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            duration_seconds=duration_ms / 1000.0,
        )
        dec_inprogress()
        # 慢请求 -> warning；正常 -> info
        log_fn = log.warning if duration_ms > SLOW_REQUEST_THRESHOLD_MS else log.info
        log_fn(
            "http.access",
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            trace_id=trace_id,
            user_id=user_id,
        )
        return response
