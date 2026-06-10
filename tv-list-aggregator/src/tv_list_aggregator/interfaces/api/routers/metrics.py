"""Prometheus HTTP 指标端点 + 指标注册。

定义在 HTTP 边界使用的指标：
- ``http_requests_total``：请求计数（method/path/status）
- ``http_request_duration_seconds``：请求延迟直方图（method/path）
- ``http_inprogress_requests``：当前正在处理的请求数（活跃连接指标）

``/metrics`` 端点返回 prometheus_client 默认注册表中的所有指标，
包含本文件新增的 HTTP 指标以及 ``tvlist_*`` 业务指标。
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

router = APIRouter(tags=["metrics"])

# 请求总数：按 method / path / status 分类
HTTP_REQUESTS_TOTAL: Counter = Counter(
    "http_requests_total",
    "Total HTTP requests processed.",
    labelnames=("method", "path", "status"),
)

# 请求耗时直方图：按 method / path 分类
HTTP_REQUEST_DURATION_SECONDS: Histogram = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    labelnames=("method", "path"),
)

# 当前正在处理的请求数（活跃连接等价指标）
HTTP_INPROGRESS_REQUESTS: Gauge = Gauge(
    "http_inprogress_requests",
    "In-progress HTTP requests.",
)


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus 指标抓取端点。"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def observe_http_request(
    *,
    method: str,
    path: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    """由中间件调用的统一打点入口。"""
    # 状态码以字符串形式写入 label，避免高基数
    status_label: str = str(status_code)
    HTTP_REQUESTS_TOTAL.labels(
        method=method, path=path, status=status_label
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(
        duration_seconds
    )


def inc_inprogress() -> None:
    """活跃请求 +1。"""
    HTTP_INPROGRESS_REQUESTS.inc()


def dec_inprogress() -> None:
    """活跃请求 -1。"""
    HTTP_INPROGRESS_REQUESTS.dec()
