"""FastAPI 应用工厂 + 启动装配。"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from ...core.logging import configure_logging, get_logger
from ...core.settings import get_settings
from ...core.tracing import init_tracer
from ...domain.services.dedup_service import DedupService
from ...domain.services.normalization_service import NormalizationService
from ...infrastructure.http.client import ResilientHTTPFetcher
from ...infrastructure.llm.prompt_loader import PromptLoader
from ...infrastructure.persistence.sqlalchemy_base import make_engine
from ...plugins.parsers.json_parser import JSONParser
from ...plugins.registry import PluginRegistry
from ...plugins.sources.http_json_source import HTTPSource
from .middleware.error_handler import ErrorHandlerMiddleware
from .middleware.rate_limit import limiter
from .middleware.request_id import RequestIDMiddleware
from .routers import admin, export, health, jobs, programs, sources

log = get_logger(__name__)


def build_registry() -> PluginRegistry:
    """构造默认插件注册表（json + html + llm 解析器；http/rss/html/m3u 源）。"""
    from ...infrastructure.llm.llm_router import LLMRouter
    from ...plugins.parsers.html_parser import HTMLParser
    from ...plugins.parsers.llm_parser import LLMParser
    from ...plugins.sources.html_scrape_source import HTMLScrapeSource
    from ...plugins.sources.m3u_source import M3USource
    from ...plugins.sources.rss_source import RSSSource

    fetcher = ResilientHTTPFetcher()
    parser = JSONParser()
    prompts = PromptLoader("src/tv_list_aggregator/infrastructure/llm/prompts")
    # LLM 路由：无密钥环境下使用 StubLLM
    from ...infrastructure.llm.stub import StubLLM

    llm = StubLLM()
    router_llm = LLMRouter(primary=llm, fallbacks=[])

    reg = PluginRegistry()
    reg.register_source("http_json", lambda: HTTPSource(fetcher=fetcher, parser=parser))
    reg.register_source("rss", lambda: RSSSource(fetcher=fetcher, parser=parser))
    reg.register_source(
        "html_scrape",
        lambda: HTMLScrapeSource(
            fetcher=None,  # type: ignore[arg-type]
            parsers=[HTMLParser(), LLMParser(llm=router_llm, prompts=prompts)],
        ),
    )
    reg.register_source("m3u", lambda: M3USource(fetcher=fetcher))

    reg.register_parser("json", parser)
    reg.register_parser("html", HTMLParser())
    reg.register_parser("llm", LLMParser(llm=router_llm, prompts=prompts))
    return reg


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    configure_logging(s.log_level)
    init_tracer("tv-list-aggregator", s.otlp_endpoint)
    log.info("app.startup", env=s.app_env)

    # 初始化全局组件并放入 app.state（DI 容器）
    registry = build_registry()
    fetcher = ResilientHTTPFetcher(rate_per_minute=s.rate_limit_per_minute)
    normalizer = NormalizationService()
    dedup = DedupService()
    json_parser = registry.get_parser("json")

    # 创建聚合服务（依赖 repo 通过 app.state 注入 session 作用域）
    # 注：AggregationService 需要在请求级构建（带 session），这里仅做占位示例
    # 实际注入由 routers 自行处理
    app.state.registry = registry
    app.state.fetcher = fetcher
    app.state.normalizer = normalizer
    app.state.dedup = dedup
    app.state.json_parser = json_parser
    app.state.engine = make_engine(s.database_url)

    yield

    log.info("app.shutdown")
    await fetcher.aclose()
    await app.state.engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="TV List Aggregator",
        version="0.1.0",
        description="多源 TV List 聚合 AI Agent",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    app.include_router(health.router)
    app.include_router(sources.router, prefix="/api/v1")
    app.include_router(programs.router, prefix="/api/v1")
    app.include_router(jobs.router, prefix="/api/v1")
    app.include_router(export.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    return app


app = create_app()
