"""FastAPI 应用工厂 + 启动装配。"""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from ...core.logging import configure_logging, get_logger
from ...core.settings import get_settings
from ...core.tracing import init_tracer
from ...domain.services.aggregation_service import AggregationService
from ...domain.services.dedup_service import DedupService
from ...domain.services.health_check_service import HealthCheckService
from ...domain.services.normalization_service import NormalizationService
from ...domain.services.source_registry import SourceRegistry
from ...infrastructure.http.client import ResilientHTTPFetcher
from ...infrastructure.http.playwright_fetcher import PlaywrightFetcher
from ...infrastructure.llm.llm_router import LLMRouter
from ...infrastructure.llm.prompt_loader import PromptLoader
from ...infrastructure.llm.stub import StubLLM
from ...infrastructure.persistence.job_repository_impl import SQLAlchemyJobRepository
from ...infrastructure.persistence.program_repository_impl import (
    SQLAlchemyProgramRepository,
)
from ...infrastructure.persistence.source_health_repository import (
    SQLAlchemySourceHealthRepository,
)
from ...infrastructure.persistence.source_repository_impl import (
    SQLAlchemySourceRepository,
)
from ...infrastructure.persistence.sqlalchemy_base import make_engine, make_session_factory
from ...infrastructure.persistence.user_repository_impl import SQLAlchemyUserRepository
from ...plugins.parsers.html_parser import HTMLParser
from ...plugins.parsers.json_parser import JSONParser
from ...plugins.parsers.llm_parser import LLMParser
from ...plugins.registry import PluginRegistry
from ...plugins.sources.html_scrape_source import HTMLScrapeSource
from ...plugins.sources.http_json_source import HTTPSource
from ...plugins.sources.m3u_source import M3USource
from ...plugins.sources.rss_source import RSSSource
from .middleware.error_handler import ErrorHandlerMiddleware
from .middleware.rate_limit import limiter
from .middleware.request_id import RequestIDMiddleware
from .routers import admin, auth, channels, dashboard, export, health, jobs, programs, sources

log = get_logger(__name__)


async def _run_alembic_upgrade(cfg) -> None:
    """在事件循环里跑 alembic upgrade head。"""
    from alembic import command as alembic_command

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, alembic_command.upgrade, cfg, "head")


def build_registry(prompts: PromptLoader, router_llm: LLMRouter) -> PluginRegistry:
    """构造默认插件注册表（json + html + llm 解析器；http/rss/html/m3u 源）。"""
    fetcher = ResilientHTTPFetcher()
    parser = JSONParser()
    playwright_fetcher = PlaywrightFetcher()  # 修复 issue #3：不再传 None

    reg = PluginRegistry()
    reg.register_source("http_json", lambda: HTTPSource(fetcher=fetcher, parser=parser))
    reg.register_source("rss", lambda: RSSSource(fetcher=fetcher, parser=parser))
    reg.register_source(
        "html_scrape",
        lambda: HTMLScrapeSource(
            fetcher=playwright_fetcher,
            parsers=[HTMLParser(), LLMParser(llm=router_llm, prompts=prompts)],
        ),
    )
    reg.register_source("m3u", lambda: M3USource(fetcher=fetcher))

    reg.register_parser("json", parser)
    reg.register_parser("html", HTMLParser())
    reg.register_parser("llm", LLMParser(llm=router_llm, prompts=prompts))
    return reg


async def _seed_default_users(session_factory) -> None:
    """根据 seed_users 配置创建/更新种子用户。dev 友好。"""
    s = get_settings()
    if s.is_production() or not s.seed_users:
        return
    from ...domain.services.auth_service import AuthService

    async with session_factory() as session:
        svc = AuthService(SQLAlchemyUserRepository(session))
        for entry in s.seed_users.split(","):
            entry = entry.strip()
            if not entry or ":" not in entry:
                continue
            parts = entry.split(":")
            if len(parts) != 3:
                continue
            username, password, role = parts
            existing = await svc.repo.get_by_username(username)
            if existing is None:
                await svc.create_user(username, password, role)
                log.info("seed.user_created", username=username, role=role)
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    configure_logging(s.log_level)
    init_tracer("tv-list-aggregator", s.otlp_endpoint)
    log.info("app.startup", env=s.app_env)

    # 修复 issue #5：默认不自动 alembic；通过 TV_LIST_AUTO_MIGRATE=1 显式启用
    if os.environ.get("TV_LIST_AUTO_MIGRATE") == "1":
        try:
            from alembic.config import Config as AlembicConfig

            cfg = AlembicConfig("alembic.ini")
            cfg.set_main_option("sqlalchemy.url", s.database_url)
            await _run_alembic_upgrade(cfg)
            log.info("app.migrations_applied")
        except Exception as e:  # noqa: BLE001
            log.warning("app.migrations_skipped", error=str(e))

    # 持久化
    engine = make_engine(s.database_url)
    session_factory = make_session_factory(engine)

    # 启动期自动建表（修复内存 SQLite / 首次启动无 alembic 的场景）：
    # - 生产 (app_env in {production, staging})：默认不自动建表，强制走 alembic 迁移
    # - 非生产 + TV_LIST_BOOTSTRAP_SCHEMA != "0"：自动 Base.metadata.create_all
    bootstrap = os.environ.get("TV_LIST_BOOTSTRAP_SCHEMA")
    if bootstrap is None:
        bootstrap = "0" if s.is_production() else "1"
    if bootstrap == "1":
        try:
            from ...infrastructure.persistence.models import Base

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            log.info("app.schema_bootstrapped", url=s.database_url.split("@")[-1])
        except Exception as e:  # noqa: BLE001
            log.warning("app.schema_bootstrap_failed", error=str(e))

    # 插件
    prompts = PromptLoader("src/tv_list_aggregator/infrastructure/llm/prompts")
    router_llm = LLMRouter(primary=StubLLM(), fallbacks=[])
    registry = build_registry(prompts, router_llm)

    fetcher = ResilientHTTPFetcher(rate_per_minute=s.rate_limit_per_minute)
    normalizer = NormalizationService()
    dedup = DedupService()

    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.registry = registry
    app.state.fetcher = fetcher
    app.state.normalizer = normalizer
    app.state.dedup = dedup
    app.state.json_parser = registry.get_parser("json")

    # seed 种子用户（dev only）
    await _seed_default_users(session_factory)

    # 注入 aggregator 工厂：每次调用都用 fresh session（admin crawl 端点用）
    class _AggFactory:
        async def run_once(self, source):
            async with session_factory() as s:
                return await AggregationService(
                    fetcher=fetcher,
                    parser=registry.get_parser("json"),
                    program_repo=SQLAlchemyProgramRepository(s),
                    job_repo=SQLAlchemyJobRepository(s),
                    dedup=dedup,
                    normalizer=normalizer,
                    session_factory=session_factory,
                ).run_once(source)

    app.state.agg = _AggFactory()

    # dev + 空库时自动 seed（让 GUI 开箱即有数据）
    if not s.is_production() and os.environ.get("TV_LIST_AUTO_SEED") != "0":
        from .seed import seed_if_empty

        try:
            stats = await seed_if_empty(session_factory)
            log.info("app.auto_seed", **stats)
        except Exception as e:  # noqa: BLE001
            log.warning("app.auto_seed_failed", error=str(e))

    # 修复 issue #6：在 lifespan 中启动 JobScheduler
    from ...interfaces.scheduler.jobs.health_check_job import health_check_loop
    from ...interfaces.scheduler.scheduler import JobScheduler

    scheduler = JobScheduler()
    app.state.scheduler = scheduler

    async def _health_tick() -> None:
        async with session_factory() as session:
            health_repo = SQLAlchemySourceHealthRepository(session)
            source_repo = SQLAlchemySourceRepository(session)
            registry_holder = SourceRegistry(source_repo, health_repo)
            svc = HealthCheckService(fetcher=fetcher, session=session)
            try:
                await health_check_loop(
                    svc=svc,
                    registry=registry_holder,
                    source_repo=source_repo,
                    health_repo=health_repo,
                )
                await session.commit()
            except Exception as e:  # noqa: BLE001
                log.error("scheduler.health_tick.failed", error=str(e))
                await session.rollback()

    # 每 5 分钟跑一次健康检查（生产可配置）
    scheduler.add_interval("health_check", seconds=300, func=_health_tick)
    scheduler.start()
    log.info("app.scheduler_started", job_id="health_check", seconds=300)

    yield

    log.info("app.shutdown")
    scheduler.shutdown()
    await fetcher.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="TV List Aggregator",
        version="0.1.0",
        description="多源 TV List 聚合 AI Agent",
        lifespan=lifespan,
    )
    app.state.limiter = limiter

    async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """HTTPException -> RFC 7807 problem+json。"""
        rid = getattr(request.state, "request_id", None) or "unknown"
        body = {
            "type": "/problems/http-error",
            "title": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
            "status": exc.status_code,
            "detail": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            "instance": str(request.url.path),
            "request_id": rid,
        }
        headers = dict(exc.headers or {})
        headers.setdefault("x-request-id", rid)
        return JSONResponse(body, status_code=exc.status_code, headers=headers)

    async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """RequestValidationError -> RFC 7807 problem+json。"""
        rid = getattr(request.state, "request_id", None) or "unknown"
        return JSONResponse(
            {
                "type": "/problems/validation-error",
                "title": "Validation Error",
                "status": 422,
                "detail": "request validation failed",
                "instance": str(request.url.path),
                "request_id": rid,
                "errors": exc.errors(),
            },
            status_code=422,
            headers={"x-request-id": rid},
        )

    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(sources.router, prefix="/api/v1")
    app.include_router(programs.router, prefix="/api/v1")
    app.include_router(channels.router, prefix="/api/v1")
    app.include_router(jobs.router, prefix="/api/v1")
    app.include_router(export.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    app.include_router(dashboard.router, prefix="/api/v1")

    # 挂载 Web GUI 静态文件（Codex 风格 dashboard）
    import os.path

    _web_dir = os.path.join(os.path.dirname(__file__), "..", "web")
    if os.path.isdir(_web_dir):
        app.mount("/static", StaticFiles(directory=_web_dir), name="static")

        # 根路径 → 返回 index.html（让 / 打开 GUI，而非 OpenAPI）
        from fastapi.responses import FileResponse

        @app.get("/", include_in_schema=False)
        async def _root() -> FileResponse:
            return FileResponse(os.path.join(_web_dir, "index.html"))

    return app


app = create_app()
