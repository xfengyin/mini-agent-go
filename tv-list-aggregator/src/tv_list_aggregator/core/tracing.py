"""OpenTelemetry Tracer 初始化与获取（可选依赖）。"""
from __future__ import annotations

import importlib
from typing import Any

_tracer: Any = None


def init_tracer(service_name: str, otlp_endpoint: str | None) -> None:
    """初始化全局 TracerProvider。

    - 未配置 endpoint：使用 noop tracer
    - 未安装 OpenTelemetry：安全降级为 noop
    - 配置了 endpoint：启用 OTLP HTTP exporter
    """
    global _tracer
    if not otlp_endpoint:
        return
    try:
        trace_mod = importlib.import_module("opentelemetry.trace")
        sdk_mod = importlib.import_module("opentelemetry.sdk.trace")
        resource_mod = importlib.import_module("opentelemetry.sdk.resources")
        processor_mod = importlib.import_module("opentelemetry.sdk.trace.export")
        exporter_mod = importlib.import_module("opentelemetry.exporter.otlp.proto.http.trace_exporter")
    except ImportError:
        return  # 优雅降级

    resource = resource_mod.Resource.create({"service.name": service_name})
    provider = sdk_mod.TracerProvider(resource=resource)
    exporter = exporter_mod.OTLPSpanExporter(endpoint=otlp_endpoint)
    provider.add_span_processor(processor_mod.BatchSpanProcessor(exporter))
    trace_mod.set_tracer_provider(provider)
    _tracer = trace_mod.get_tracer(service_name)


def get_tracer(name: str) -> Any:
    """获取 Tracer（未启用时返回 noop）。"""
    global _tracer
    if _tracer is not None:
        return _tracer
    try:
        trace_mod = importlib.import_module("opentelemetry.trace")
        return trace_mod.get_tracer(name)
    except ImportError:
        return None
