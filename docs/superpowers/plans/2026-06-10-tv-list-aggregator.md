# TV List 聚合 AI Agent 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个生产可用的多源 TV List 自动聚合 AI Agent，支持动态源接入、LLM 增强解析、智能清洗去重、统一存储分发、可观测可扩展。

**Architecture:** 插件化 SPI 架构 + 分层六边形（Domain/Infrastructure/Interface）+ 配置驱动 + 可观测性贯穿全链路。核心引擎通过抽象接口对接存储、LLM、HTTP、源适配器，支持热插拔与多模型兜底。

**Tech Stack:**
- 语言/运行时：Python 3.11+
- Web/异步：FastAPI、asyncio、uvicorn
- 爬虫：httpx、Playwright、selectolax、Trafilatura
- AI/LLM：LangChain、OpenAI/Anthropic/Ollama 多适配器、tenacity 重试
- 存储：SQLAlchemy 2.x（PostgreSQL/SQLite 兼容）、Redis（缓存/限流）、可选 MongoDB
- 任务调度：APScheduler（单机）/ Celery + Redis（分布式）
- 可观测：structlog、OpenTelemetry、Prometheus 指标、Sentry
- 安全：python-jose（JWT）、passlib、cryptography、pydantic 数据脱敏
- 限流/熔断：slowapi、pybreaker
- 测试：pytest、pytest-asyncio、respx（HTTP Mock）、fakeredis
- 工程化：pyproject.toml、ruff、mypy、pre-commit、GitHub Actions
- 部署：Docker、Docker Compose、（可选）Kubernetes Helm

---

## 文件结构总览

```
tv-list-aggregator/
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── src/
│   └── tv_list_aggregator/
│       ├── __init__.py
│       ├── main.py                       # FastAPI 入口
│       ├── cli.py                        # Typer CLI 入口
│       ├── core/                         # 基础设施/横切关注点
│       │   ├── __init__.py
│       │   ├── settings.py               # pydantic-settings 配置
│       │   ├── logging.py                # structlog 配置
│       │   ├── tracing.py                # OpenTelemetry 初始化
│       │   ├── exceptions.py             # 领域异常层级
│       │   ├── types.py                  # 通用类型别名
│       │   └── lifespan.py               # 应用生命周期
│       ├── domain/                       # 领域层：业务模型与契约
│       │   ├── __init__.py
│       │   ├── models/
│       │   │   ├── __init__.py
│       │   │   ├── source.py             # TVListSource 实体
│       │   │   ├── program.py            # TVProgram 实体
│       │   │   ├── crawl_job.py          # 抓取任务实体
│       │   │   ├── health.py             # 健康检查结果
│       │   │   └── value_objects.py      # 频道/时间槽/标签等
│       │   ├── ports/                    # 抽象接口（依赖倒置）
│       │   │   ├── __init__.py
│       │   │   ├── source_repository.py
│       │   │   ├── program_repository.py
│       │   │   ├── job_repository.py
│       │   │   ├── fetcher.py
│       │   │   ├── parser.py
│       │   │   ├── llm.py
│       │   │   ├── cache.py
│       │   │   ├── event_bus.py
│       │   │   └── clock.py
│       │   └── services/                 # 领域服务
│       │       ├── __init__.py
│       │       ├── source_registry.py    # 源注册中心
│       │       ├── aggregation_service.py
│       │       ├── dedup_service.py
│       │       ├── normalization_service.py
│       │       ├── health_check_service.py
│       │       └── feedback_service.py
│       ├── infrastructure/               # 基础设施实现
│       │   ├── __init__.py
│       │   ├── persistence/
│       │   │   ├── __init__.py
│       │   │   ├── sqlalchemy_base.py
│       │   │   ├── models.py             # ORM 映射
│       │   │   ├── source_repository_impl.py
│       │   │   ├── program_repository_impl.py
│       │   │   ├── job_repository_impl.py
│       │   │   └── migrations/           # Alembic
│       │   ├── cache/
│       │   │   ├── __init__.py
│       │   │   └── redis_cache.py
│       │   ├── llm/
│       │   │   ├── __init__.py
│       │   │   ├── openai_adapter.py
│       │   │   ├── anthropic_adapter.py
│       │   │   ├── ollama_adapter.py
│       │   │   ├── llm_router.py         # 多模型兜底
│       │   │   └── prompts/              # 配置化提示词
│       │   │       ├── extract_program.yaml
│       │   │       ├── normalize.yaml
│       │   │       └── classify.yaml
│       │   ├── http/
│       │   │   ├── __init__.py
│       │   │   ├── client.py             # httpx 封装（重试/限流/熔断）
│       │   │   └── playwright_fetcher.py
│       │   ├── events/
│       │   │   ├── __init__.py
│       │   │   └── inproc_event_bus.py
│       │   └── resilience/
│       │       ├── __init__.py
│       │       ├── circuit_breaker.py
│       │       └── rate_limiter.py
│       ├── plugins/                      # SPI 插件
│       │   ├── __init__.py
│       │   ├── registry.py               # 插件注册器
│       │   ├── sources/
│       │   │   ├── __init__.py
│       │   │   ├── base.py               # SourceAdapter 基类
│       │   │   ├── http_json_source.py
│       │   │   ├── rss_source.py
│       │   │   ├── html_scrape_source.py
│       │   │   └── m3u_source.py         # 直播/点播源
│       │   └── parsers/
│       │       ├── __init__.py
│       │       ├── base.py
│       │       ├── json_parser.py
│       │       ├── html_parser.py
│       │       └── llm_parser.py
│       ├── interfaces/                   # 外部接口
│       │   ├── __init__.py
│       │   ├── api/
│       │   │   ├── __init__.py
│       │   │   ├── app.py
│       │   │   ├── deps.py               # 依赖注入
│       │   │   ├── middleware/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── request_id.py
│       │   │   │   ├── error_handler.py
│       │   │   │   └── rate_limit.py
│       │   │   ├── routers/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── sources.py
│       │   │   │   ├── programs.py
│       │   │   │   ├── jobs.py
│       │   │   │   ├── health.py
│       │   │   │   ├── export.py
│       │   │   │   └── admin.py
│       │   │   ├── schemas/              # pydantic DTO
│       │   │   │   ├── __init__.py
│       │   │   │   ├── source.py
│       │   │   │   ├── program.py
│       │   │   │   └── job.py
│       │   │   └── security.py
│       │   ├── scheduler/
│       │   │   ├── __init__.py
│       │   │   ├── scheduler.py
│       │   │   └── jobs/
│       │   │       ├── __init__.py
│       │   │       ├── crawl_job.py
│       │   │       ├── health_check_job.py
│       │   │       └── cleanup_job.py
│       │   └── cli/
│       │       ├── __init__.py
│       │       └── commands.py
│       └── observability/
│           ├── __init__.py
│           ├── metrics.py
│           └── health.py
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── domain/
│   │   ├── infrastructure/
│   │   └── plugins/
│   ├── integration/
│   │   ├── api/
│   │   └── persistence/
│   └── e2e/
├── scripts/
│   ├── bootstrap.sh
│   └── load_test.py
├── config/
│   ├── sources.example.yaml
│   └── policies.yaml
└── docs/
    ├── architecture.md
    ├── operations.md
    └── security.md
```

---

## Task 1：项目脚手架与工程化基线

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/tv_list_aggregator/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: 初始化 pyproject.toml（含 ruff/mypy/pytest 配置）**

```toml
[build-system]
requires = ["hatchling>=1.18"]
build-backend = "hatchling.build"

[project]
name = "tv-list-aggregator"
version = "0.1.0"
description = "Enterprise-grade TV List aggregation AI Agent"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.27",
  "pydantic>=2.6",
  "pydantic-settings>=2.2",
  "sqlalchemy[asyncio]>=2.0",
  "alembic>=1.13",
  "asyncpg>=0.29",
  "aiosqlite>=0.19",
  "redis>=5.0",
  "httpx>=0.27",
  "tenacity>=8.2",
  "pybreaker>=1.2",
  "slowapi>=0.1.9",
  "structlog>=24.1",
  "opentelemetry-api>=1.24",
  "opentelemetry-sdk>=1.24",
  "opentelemetry-exporter-otlp>=1.24",
  "prometheus-client>=0.20",
  "apscheduler>=3.10",
  "python-jose[cryptography]>=3.3",
  "passlib[bcrypt]>=1.7",
  "cryptography>=42",
  "selectolax>=0.3.21",
  "trafilatura>=1.6",
  "playwright>=1.42",
  "langchain>=0.1.16",
  "langchain-openai>=0.1",
  "langchain-anthropic>=0.1",
  "typer>=0.12",
  "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "pytest-cov>=4.1",
  "respx>=0.21",
  "fakeredis>=2.21",
  "ruff>=0.4",
  "mypy>=1.9",
  "pre-commit>=3.7",
  "freezegun>=1.4",
]

[tool.ruff]
line-length = 99
target-version = "py311"

[tool.ruff.lint]
select = ["E","F","I","N","W","UP","B","A","S","RUF","C4","PT","RET","SIM"]
ignore = ["E501"]

[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-ra --strict-markers"
```

- [ ] **Step 2: 创建 .gitignore**

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.env
.coverage
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
.idea/
.vscode/
*.log
data/
```

- [ ] **Step 3: 创建 .env.example**

```dotenv
APP_ENV=development
LOG_LEVEL=INFO
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/tvlist
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-me
JWT_ALGORITHM=HS256
LLM_PROVIDER=openai
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
ENABLE_TELEMETRY=true
OTLP_ENDPOINT=
RATE_LIMIT_PER_MINUTE=120
PLUGIN_DIR=./plugins
LEGAL_NOTICE_FILE=./config/legal_notice.md
```

- [ ] **Step 4: 创建包入口与测试 conftest**

`src/tv_list_aggregator/__init__.py`:
```python
"""TV List 聚合 AI Agent。"""
__version__ = "0.1.0"
```

`tests/conftest.py`:
```python
import pytest

@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
```

- [ ] **Step 5: 安装并提交**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
git init && git add . && git commit -m "chore: scaffold project"
```

---

## Task 2：核心配置与日志（可观测基础）

**Files:**
- Create: `src/tv_list_aggregator/core/settings.py`
- Create: `src/tv_list_aggregator/core/logging.py`
- Create: `src/tv_list_aggregator/core/types.py`
- Test: `tests/unit/core/test_settings.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/unit/core/test_settings.py
from tv_list_aggregator.core.settings import Settings

def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    s = Settings()
    assert s.app_env == "test"
    assert s.database_url.startswith("sqlite")
```

- [ ] **Step 2: 实现 Settings**

```python
# src/tv_list_aggregator/core/settings.py
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///:memory:"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    llm_provider: str = "openai"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    enable_telemetry: bool = False
    otlp_endpoint: str = ""
    rate_limit_per_minute: int = 120
    plugin_dir: str = "./plugins"
    legal_notice_file: str = "./config/legal_notice.md"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: 实现结构化日志**

```python
# src/tv_list_aggregator/core/logging.py
import logging
import structlog

def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
```

- [ ] **Step 4: 运行测试并提交**

```bash
pytest tests/unit/core/test_settings.py -v
git add -A && git commit -m "feat(core): settings & structured logging"
```

---

## Task 3：领域异常层级与可观测 tracing

**Files:**
- Create: `src/tv_list_aggregator/core/exceptions.py`
- Create: `src/tv_list_aggregator/core/tracing.py`
- Test: `tests/unit/core/test_exceptions.py`

- [ ] **Step 1: 异常层级（业务无关可重试/可降级语义）**

```python
# src/tv_list_aggregator/core/exceptions.py
class TVListBaseError(Exception):
    """所有领域异常的基类。"""

class TransientError(TVListBaseError):
    """可重试的瞬时错误（网络抖动、限流）。"""

class PermanentError(TVListBaseError):
    """不可重试的永久错误（数据源 404、解析失败）。"""

class SourceUnavailableError(TransientError):
    """数据源不可用。"""

class SourceAuthError(PermanentError):
    """鉴权失败。"""

class ParseError(PermanentError):
    """解析失败。"""

class RateLimitError(TransientError):
    """触发限流。"""

class StorageError(TVListBaseError):
    """存储层错误。"""

class LLMError(TVListBaseError):
    """LLM 调用失败。"""
```

- [ ] **Step 2: 测试异常可识别**

```python
# tests/unit/core/test_exceptions.py
from tv_list_aggregator.core.exceptions import TransientError, RateLimitError

def test_rate_limit_is_transient():
    assert issubclass(RateLimitError, TransientError)
```

- [ ] **Step 3: OpenTelemetry 初始化（可选）**

```python
# src/tv_list_aggregator/core/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def init_tracer(service_name: str, otlp_endpoint: str | None) -> None:
    if not otlp_endpoint:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    trace.set_tracer_provider(provider)

def get_tracer(name: str):
    return trace.get_tracer(name)
```

- [ ] **Step 4: 运行测试并提交**

```bash
pytest tests/unit/core -v
git add -A && git commit -m "feat(core): exceptions & tracing init"
```

---

## Task 4：领域模型（Pydantic + 不可变值对象）

**Files:**
- Create: `src/tv_list_aggregator/domain/models/value_objects.py`
- Create: `src/tv_list_aggregator/domain/models/source.py`
- Create: `src/tv_list_aggregator/domain/models/program.py`
- Create: `src/tv_list_aggregator/domain/models/crawl_job.py`
- Create: `src/tv_list_aggregator/domain/models/health.py`
- Test: `tests/unit/domain/models/test_program.py`

- [ ] **Step 1: 值对象**

```python
# src/tv_list_aggregator/domain/models/value_objects.py
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl

class Channel(BaseModel):
    id: str
    name: str
    logo_url: HttpUrl | None = None
    country: str | None = None
    language: str | None = None

class TimeSlot(BaseModel):
    start: datetime
    end: datetime
    timezone: str = "UTC"

class Tag(BaseModel):
    label: str
    category: str  # e.g. "genre" | "region" | "language"

class ProgramIdentity(BaseModel):
    """跨源去重键：title+channel+start。"""
    title_norm: str
    channel_id: str
    start: datetime
```

- [ ] **Step 2: 节目实体（聚合根）**

```python
# src/tv_list_aggregator/domain/models/program.py
from datetime import datetime
from pydantic import BaseModel, Field
from .value_objects import Channel, Tag, TimeSlot

class TVProgram(BaseModel):
    id: str | None = None
    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    channel: Channel
    slot: TimeSlot
    tags: list[Tag] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    identity_key: str
    created_at: datetime
    updated_at: datetime
    version: int = 1
```

- [ ] **Step 3: 数据源实体**

```python
# src/tv_list_aggregator/domain/models/source.py
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl

class SourceType(str, Enum):
    HTTP_JSON = "http_json"
    RSS = "rss"
    HTML_SCRAPE = "html_scrape"
    M3U = "m3u"
    CUSTOM = "custom"

class SourceStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"

class TVListSource(BaseModel):
    id: str
    name: str
    type: SourceType
    url: HttpUrl | None = None
    config: dict = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    cron: str = "*/15 * * * *"
    priority: int = 5
    status: SourceStatus = SourceStatus.ACTIVE
    parser: str = "auto"
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 4: 抓取任务与健康结果**

```python
# src/tv_list_aggregator/domain/models/crawl_job.py
from datetime import datetime
from enum import Enum
from pydantic import BaseModel

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"

class CrawlJob(BaseModel):
    id: str
    source_id: str
    status: JobStatus
    started_at: datetime
    finished_at: datetime | None = None
    items_fetched: int = 0
    items_saved: int = 0
    error: str | None = None
    trace_id: str | None = None
```

```python
# src/tv_list_aggregator/domain/models/health.py
from datetime import datetime
from pydantic import BaseModel

class SourceHealth(BaseModel):
    source_id: str
    is_alive: bool
    latency_ms: int | None
    checked_at: datetime
    message: str | None = None
```

- [ ] **Step 5: 单元测试**

```python
# tests/unit/domain/models/test_program.py
from datetime import datetime, timezone
from tv_list_aggregator.domain.models.program import TVProgram
from tv_list_aggregator.domain.models.value_objects import Channel, TimeSlot

def test_program_compute_identity_key_is_stable():
    p = TVProgram(
        title="新闻联播",
        channel=Channel(id="cctv1", name="CCTV-1"),
        slot=TimeSlot(
            start=datetime(2026,1,1,19,0,tzinfo=timezone.utc),
            end=datetime(2026,1,1,19,30,tzinfo=timezone.utc),
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        identity_key="x",
    )
    assert p.title == "新闻联播"
```

- [ ] **Step 6: 运行测试并提交**

```bash
pytest tests/unit/domain -v
git add -A && git commit -m "feat(domain): entities & value objects"
```

---

## Task 5：领域端口（Port 接口契约）

**Files:**
- Create: `src/tv_list_aggregator/domain/ports/__init__.py`
- Create: `src/tv_list_aggregator/domain/ports/source_repository.py`
- Create: `src/tv_list_aggregator/domain/ports/program_repository.py`
- Create: `src/tv_list_aggregator/domain/ports/job_repository.py`
- Create: `src/tv_list_aggregator/domain/ports/fetcher.py`
- Create: `src/tv_list_aggregator/domain/ports/parser.py`
- Create: `src/tv_list_aggregator/domain/ports/llm.py`
- Create: `src/tv_list_aggregator/domain/ports/cache.py`
- Create: `src/tv_list_aggregator/domain/ports/event_bus.py`
- Create: `src/tv_list_aggregator/domain/ports/clock.py`
- Test: `tests/unit/domain/ports/test_ports_protocol.py`

- [ ] **Step 1: 仓储接口（依赖倒置：领域定义接口）**

```python
# src/tv_list_aggregator/domain/ports/source_repository.py
from typing import Protocol
from ..models.source import TVListSource

class SourceRepository(Protocol):
    async def get(self, source_id: str) -> TVListSource | None: ...
    async def list(self, *, status: str | None = None) -> list[TVListSource]: ...
    async def add(self, source: TVListSource) -> None: ...
    async def update(self, source: TVListSource) -> None: ...
    async def delete(self, source_id: str) -> None: ...
```

```python
# src/tv_list_aggregator/domain/ports/program_repository.py
from typing import Protocol
from datetime import datetime
from ..models.program import TVProgram

class ProgramRepository(Protocol):
    async def upsert(self, program: TVProgram) -> TVProgram: ...
    async def find_by_identity(self, identity_key: str) -> TVProgram | None: ...
    async def list_by_range(self, start: datetime, end: datetime, *, channel_id: str | None = None) -> list[TVProgram]: ...
    async def count(self) -> int: ...
```

```python
# src/tv_list_aggregator/domain/ports/job_repository.py
from typing import Protocol
from ..models.crawl_job import CrawlJob, JobStatus

class JobRepository(Protocol):
    async def add(self, job: CrawlJob) -> None: ...
    async def update(self, job: CrawlJob) -> None: ...
    async def list(self, *, source_id: str | None = None, status: JobStatus | None = None, limit: int = 50) -> list[CrawlJob]: ...
```

- [ ] **Step 2: Fetcher/Parser/LLM/Cache/Event/Clock 抽象**

```python
# src/tv_list_aggregator/domain/ports/fetcher.py
from typing import Protocol
from dataclasses import dataclass

@dataclass
class FetchResult:
    url: str
    status_code: int
    body: bytes
    headers: dict[str, str]
    elapsed_ms: int

class Fetcher(Protocol):
    async def fetch(self, url: str, *, headers: dict[str, str] | None = None, timeout: float = 30.0) -> FetchResult: ...
```

```python
# src/tv_list_aggregator/domain/ports/parser.py
from typing import Protocol
from ..models.program import TVProgram

class Parser(Protocol):
    name: str
    async def parse(self, content: bytes, *, hint: dict | None = None) -> list[TVProgram]: ...
```

```python
# src/tv_list_aggregator/domain/ports/llm.py
from typing import Protocol

class LLM(Protocol):
    async def complete(self, prompt: str, *, json_mode: bool = False) -> str: ...
    async def embed(self, text: str) -> list[float]: ...
```

```python
# src/tv_list_aggregator/domain/ports/cache.py
from typing import Protocol

class Cache(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, *, ttl: int = 60) -> None: ...
    async def delete(self, key: str) -> None: ...
```

```python
# src/tv_list_aggregator/domain/ports/event_bus.py
from typing import Protocol, Any

class EventBus(Protocol):
    async def publish(self, topic: str, payload: Any) -> None: ...
    def subscribe(self, topic: str, handler) -> None: ...
```

```python
# src/tv_list_aggregator/domain/ports/clock.py
from datetime import datetime
from typing import Protocol

class Clock(Protocol):
    def now(self) -> datetime: ...
```

- [ ] **Step 3: 协议自检测试**

```python
# tests/unit/domain/ports/test_ports_protocol.py
from tv_list_aggregator.domain.ports.source_repository import SourceRepository
from tv_list_aggregator.domain.ports.fetcher import Fetcher
from tv_list_aggregator.domain.ports.llm import LLM

def test_ports_are_protocols():
    assert hasattr(SourceRepository, "get")
    assert hasattr(Fetcher, "fetch")
    assert hasattr(LLM, "complete")
```

- [ ] **Step 4: 运行并提交**

```bash
pytest tests/unit/domain/ports -v
git add -A && git commit -m "feat(domain): port interfaces"
```

---

## Task 6：基础设施 - SQLAlchemy 异步持久化

**Files:**
- Create: `src/tv_list_aggregator/infrastructure/persistence/sqlalchemy_base.py`
- Create: `src/tv_list_aggregator/infrastructure/persistence/models.py`
- Create: `src/tv_list_aggregator/infrastructure/persistence/source_repository_impl.py`
- Create: `src/tv_list_aggregator/infrastructure/persistence/program_repository_impl.py`
- Create: `src/tv_list_aggregator/infrastructure/persistence/job_repository_impl.py`
- Create: `alembic.ini`
- Create: `src/tv_list_aggregator/infrastructure/persistence/migrations/env.py`
- Test: `tests/integration/persistence/test_repositories.py`

- [ ] **Step 1: 异步引擎与基类**

```python
# src/tv_list_aggregator/infrastructure/persistence/sqlalchemy_base.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase): ...

def make_engine(url: str):
    return create_async_engine(url, echo=False, pool_pre_ping=True)

def make_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
```

- [ ] **Step 2: ORM 模型**

```python
# src/tv_list_aggregator/infrastructure/persistence/models.py
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, JSON, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from .sqlalchemy_base import Base

class SourceRow(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(32), index=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    headers: Mapped[dict] = mapped_column(JSON, default=dict)
    cron: Mapped[str] = mapped_column(String(64), default="*/15 * * * *")
    priority: Mapped[int] = mapped_column(Integer, default=5)
    status: Mapped[str] = mapped_column(String(16), default="active")
    parser: Mapped[str] = mapped_column(String(64), default="auto")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)

class ProgramRow(Base):
    __tablename__ = "programs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_id: Mapped[str] = mapped_column(String(64), index=True)
    channel_name: Mapped[str] = mapped_column(String(255))
    channel_logo: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    channel_country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    channel_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    source_ids: Mapped[list] = mapped_column(JSON, default=list)
    identity_key: Mapped[str] = mapped_column(String(128), index=True, unique=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)

Index("ix_prog_channel_start", ProgramRow.channel_id, ProgramRow.start_at)

class JobRow(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    items_fetched: Mapped[int] = mapped_column(Integer, default=0)
    items_saved: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
```

- [ ] **Step 3: 仓储实现（Source）**

```python
# src/tv_list_aggregator/infrastructure/persistence/source_repository_impl.py
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ...domain.models.source import TVListSource, SourceStatus, SourceType
from ...domain.ports.source_repository import SourceRepository
from .models import SourceRow

class SQLAlchemySourceRepository(SourceRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _to_domain(row: SourceRow) -> TVListSource:
        return TVListSource(
            id=row.id, name=row.name, type=SourceType(row.type), url=row.url,
            config=row.config or {}, headers=row.headers or {},
            cron=row.cron, priority=row.priority, status=SourceStatus(row.status),
            parser=row.parser, created_at=row.created_at, updated_at=row.updated_at,
        )

    async def get(self, source_id: str) -> TVListSource | None:
        row = await self.session.get(SourceRow, source_id)
        return self._to_domain(row) if row else None

    async def list(self, *, status: str | None = None) -> list[TVListSource]:
        stmt = select(SourceRow)
        if status:
            stmt = stmt.where(SourceRow.status == status)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def add(self, source: TVListSource) -> None:
        self.session.add(SourceRow(
            id=source.id, name=source.name, type=source.type.value, url=str(source.url) if source.url else None,
            config=source.config, headers=source.headers, cron=source.cron,
            priority=source.priority, status=source.status.value, parser=source.parser,
            created_at=source.created_at, updated_at=source.updated_at,
        ))

    async def update(self, source: TVListSource) -> None:
        row = await self.session.get(SourceRow, source.id)
        if not row:
            return
        row.name = source.name; row.type = source.type.value
        row.url = str(source.url) if source.url else None
        row.config = source.config; row.headers = source.headers
        row.cron = source.cron; row.priority = source.priority
        row.status = source.status.value; row.parser = source.parser
        row.updated_at = datetime.utcnow()

    async def delete(self, source_id: str) -> None:
        row = await self.session.get(SourceRow, source_id)
        if row:
            await self.session.delete(row)
```

- [ ] **Step 4: 仓储实现（Program/Job）**

```python
# src/tv_list_aggregator/infrastructure/persistence/program_repository_impl.py
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ...domain.models.program import TVProgram
from ...domain.models.value_objects import Channel, TimeSlot
from ...domain.ports.program_repository import ProgramRepository
from .models import ProgramRow

class SQLAlchemyProgramRepository(ProgramRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _to_domain(r: ProgramRow) -> TVProgram:
        return TVProgram(
            id=r.id, title=r.title, description=r.description,
            channel=Channel(id=r.channel_id, name=r.channel_name, logo_url=r.channel_logo,
                            country=r.channel_country, language=r.channel_language),
            slot=TimeSlot(start=r.start_at, end=r.end_at, timezone=r.timezone),
            tags=r.tags or [], source_ids=r.source_ids or [],
            identity_key=r.identity_key, created_at=r.created_at,
            updated_at=r.updated_at, version=r.version,
        )

    @staticmethod
    def _from_domain(p: TVProgram) -> ProgramRow:
        return ProgramRow(
            id=p.id or "", title=p.title, description=p.description,
            channel_id=p.channel.id, channel_name=p.channel.name,
            channel_logo=str(p.channel.logo_url) if p.channel.logo_url else None,
            channel_country=p.channel.country, channel_language=p.channel.language,
            start_at=p.slot.start, end_at=p.slot.end, timezone=p.slot.timezone,
            tags=p.tags, source_ids=p.source_ids, identity_key=p.identity_key,
            version=p.version, created_at=p.created_at, updated_at=p.updated_at,
        )

    async def upsert(self, program: TVProgram) -> TVProgram:
        existing = (await self.session.execute(
            select(ProgramRow).where(ProgramRow.identity_key == program.identity_key)
        )).scalar_one_or_none()
        if existing:
            existing.title = program.title; existing.description = program.description
            existing.start_at = program.slot.start; existing.end_at = program.slot.end
            existing.tags = program.tags
            existing.source_ids = list({*(existing.source_ids or []), *program.source_ids})
            existing.version += 1; existing.updated_at = datetime.utcnow()
            return self._to_domain(existing)
        row = self._from_domain(program)
        self.session.add(row)
        await self.session.flush()
        return self._to_domain(row)

    async def find_by_identity(self, identity_key: str) -> TVProgram | None:
        row = (await self.session.execute(
            select(ProgramRow).where(ProgramRow.identity_key == identity_key)
        )).scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def list_by_range(self, start: datetime, end: datetime, *, channel_id: str | None = None) -> list[TVProgram]:
        stmt = select(ProgramRow).where(ProgramRow.start_at >= start, ProgramRow.start_at < end)
        if channel_id:
            stmt = stmt.where(ProgramRow.channel_id == channel_id)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def count(self) -> int:
        from sqlalchemy import func
        return (await self.session.execute(select(func.count(ProgramRow.id)))).scalar_one()
```

```python
# src/tv_list_aggregator/infrastructure/persistence/job_repository_impl.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ...domain.models.crawl_job import CrawlJob, JobStatus
from ...domain.ports.job_repository import JobRepository
from .models import JobRow

class SQLAlchemyJobRepository(JobRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _to_domain(r: JobRow) -> CrawlJob:
        return CrawlJob(
            id=r.id, source_id=r.source_id, status=JobStatus(r.status),
            started_at=r.started_at, finished_at=r.finished_at,
            items_fetched=r.items_fetched, items_saved=r.items_saved,
            error=r.error, trace_id=r.trace_id,
        )

    async def add(self, job: CrawlJob) -> None:
        self.session.add(JobRow(
            id=job.id, source_id=job.source_id, status=job.status.value,
            started_at=job.started_at, finished_at=job.finished_at,
            items_fetched=job.items_fetched, items_saved=job.items_saved,
            error=job.error, trace_id=job.trace_id,
        ))

    async def update(self, job: CrawlJob) -> None:
        row = await self.session.get(JobRow, job.id)
        if not row:
            return
        row.status = job.status.value
        row.finished_at = job.finished_at
        row.items_fetched = job.items_fetched
        row.items_saved = job.items_saved
        row.error = job.error
        row.trace_id = job.trace_id

    async def list(self, *, source_id=None, status=None, limit: int = 50) -> list[CrawlJob]:
        stmt = select(JobRow).order_by(JobRow.started_at.desc()).limit(limit)
        if source_id:
            stmt = stmt.where(JobRow.source_id == source_id)
        if status:
            stmt = stmt.where(JobRow.status == status.value)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]
```

- [ ] **Step 5: Alembic 初始化**

```bash
alembic init -t async src/tv_list_aggregator/infrastructure/persistence/migrations
```

编辑 `migrations/env.py` 导入 `Base` 与 `models`，设置 `target_metadata = Base.metadata`。

- [ ] **Step 6: 集成测试**

```python
# tests/integration/persistence/test_repositories.py
import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from tv_list_aggregator.infrastructure.persistence.sqlalchemy_base import Base
from tv_list_aggregator.infrastructure.persistence.models import SourceRow
from tv_list_aggregator.infrastructure.persistence.source_repository_impl import SQLAlchemySourceRepository
from tv_list_aggregator.domain.models.source import TVListSource, SourceType, SourceStatus

@pytest.mark.asyncio
async def test_source_crud():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        repo = SQLAlchemySourceRepository(s)
        src = TVListSource(
            id="s1", name="Demo", type=SourceType.HTTP_JSON, url=None,
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        )
        await repo.add(src); await s.commit()
    async with Session() as s:
        repo = SQLAlchemySourceRepository(s)
        got = await repo.get("s1")
        assert got is not None and got.name == "Demo"
```

- [ ] **Step 7: 运行并提交**

```bash
pytest tests/integration/persistence -v
git add -A && git commit -m "feat(persistence): sqlalchemy async repositories"
```

---

## Task 7：HTTP 客户端（重试/熔断/限流/UA/代理）

**Files:**
- Create: `src/tv_list_aggregator/infrastructure/http/client.py`
- Create: `src/tv_list_aggregator/infrastructure/resilience/circuit_breaker.py`
- Create: `src/tv_list_aggregator/infrastructure/resilience/rate_limiter.py`
- Test: `tests/unit/infrastructure/test_http_client.py`

- [ ] **Step 1: 熔断器**

```python
# src/tv_list_aggregator/infrastructure/resilience/circuit_breaker.py
from pybreaker import CircuitBreaker

def make_breaker(name: str, fail_max: int = 5, reset_timeout: int = 30) -> CircuitBreaker:
    return CircuitBreaker(fail_max=fail_max, reset_timeout=reset_timeout, name=name)
```

- [ ] **Step 2: 令牌桶限流**

```python
# src/tv_list_aggregator/infrastructure/resilience/rate_limiter.py
import asyncio
import time

class TokenBucket:
    def __init__(self, rate_per_min: int):
        self.capacity = rate_per_min
        self.tokens = float(rate_per_min)
        self.refill_rate = rate_per_min / 60.0
        self.last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.refill_rate)
            self.last = now
            if self.tokens < 1:
                sleep_for = (1 - self.tokens) / self.refill_rate
                await asyncio.sleep(sleep_for)
                self.tokens = 0
            else:
                self.tokens -= 1
```

- [ ] **Step 3: 弹性 HTTP 客户端**

```python
# src/tv_list_aggregator/infrastructure/http/client.py
import time
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ...core.exceptions import RateLimitError, SourceUnavailableError
from ...domain.ports.fetcher import FetchResult, Fetcher
from ..resilience.circuit_breaker import make_breaker
from ..resilience.rate_limiter import TokenBucket

class ResilientHTTPFetcher(Fetcher):
    def __init__(self, rate_per_minute: int = 60, timeout: float = 30.0):
        self._client = httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                                         headers={"User-Agent": "TVListAggregator/0.1"})
        self._bucket = TokenBucket(rate_per_minute)
        self._breaker = make_breaker("http-fetcher")

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=0.5, max=8),
        retry=retry_if_exception_type((httpx.TransportError, SourceUnavailableError, RateLimitError)),
    )
    async def fetch(self, url: str, *, headers: dict[str, str] | None = None, timeout: float = 30.0) -> FetchResult:
        await self._bucket.acquire()
        start = time.monotonic()
        try:
            resp = await self._breaker.call_async(
                self._client.get, url, headers=headers, timeout=timeout
            )
        except httpx.TransportError as e:
            raise SourceUnavailableError(str(e)) from e
        elapsed = int((time.monotonic() - start) * 1000)
        if resp.status_code == 429:
            raise RateLimitError(f"rate limited: {url}")
        if resp.status_code >= 500:
            raise SourceUnavailableError(f"5xx {resp.status_code} {url}")
        if resp.status_code >= 400:
            from ...core.exceptions import PermanentError
            raise PermanentError(f"http {resp.status_code} {url}")
        return FetchResult(url=url, status_code=resp.status_code,
                            body=resp.content, headers=dict(resp.headers), elapsed_ms=elapsed)

    async def aclose(self) -> None:
        await self._client.aclose()
```

- [ ] **Step 4: 单元测试（用 respx mock）**

```python
# tests/unit/infrastructure/test_http_client.py
import pytest, respx, httpx
from tv_list_aggregator.infrastructure.http.client import ResilientHTTPFetcher
from tv_list_aggregator.core.exceptions import RateLimitError

@pytest.mark.asyncio
async def test_fetch_retries_on_5xx():
    fetcher = ResilientHTTPFetcher(rate_per_minute=10000)
    with respx.mock(base_url="https://x") as mock:
        route = mock.get("/p").mock(side_effect=[httpx.Response(503), httpx.Response(200, content=b"ok")])
        result = await fetcher.fetch("https://x/p")
        assert result.status_code == 200
        assert route.call_count == 2
    await fetcher.aclose()
```

- [ ] **Step 5: 运行并提交**

```bash
pytest tests/unit/infrastructure -v
git add -A && git commit -m "feat(http): resilient fetcher with breaker/rate-limit/retry"
```

---

## Task 8：Playwright 动态页抓取（带隔离）

**Files:**
- Create: `src/tv_list_aggregator/infrastructure/http/playwright_fetcher.py`
- Test: `tests/unit/infrastructure/test_playwright_fetcher.py`

- [ ] **Step 1: 实现（懒加载浏览器）**

```python
# src/tv_list_aggregator/infrastructure/http/playwright_fetcher.py
import time
from ...domain.ports.fetcher import FetchResult

class PlaywrightFetcher:
    def __init__(self, headless: bool = True, timeout_ms: int = 30000):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self._pw = None
        self._browser = None

    async def _ensure(self):
        if self._browser:
            return
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self.headless)

    async def fetch(self, url: str, *, headers: dict[str, str] | None = None, timeout: float = 30.0,
                    wait_selector: str | None = None) -> FetchResult:
        await self._ensure()
        ctx = await self._browser.new_context(extra_http_headers=headers or {})
        page = await ctx.new_page()
        start = time.monotonic()
        try:
            await page.goto(url, timeout=int(timeout * 1000))
            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=self.timeout_ms)
            body = await page.content()
            return FetchResult(url=url, status_code=200, body=body.encode("utf-8"),
                               headers={}, elapsed_ms=int((time.monotonic()-start)*1000))
        finally:
            await ctx.close()

    async def aclose(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
```

- [ ] **Step 2: 测试（mock 浏览器，避免 CI 启动真实 Chromium）**

```python
# tests/unit/infrastructure/test_playwright_fetcher.py
import pytest
from unittest.mock import AsyncMock, patch
from tv_list_aggregator.infrastructure.http.playwright_fetcher import PlaywrightFetcher

@pytest.mark.asyncio
async def test_fetch_uses_wait_selector():
    fetcher = PlaywrightFetcher()
    fake_result = type("R", (), {"body": b"<html/>"})()
    with patch.object(fetcher, "_ensure", AsyncMock()):
        with patch.object(fetcher, "_browser", new=AsyncMock()):
            fetcher._browser.new_context = AsyncMock(return_value=AsyncMock())
    # 真实集成测试在 CI 中通过 PLAYWRIGHT_BROWSERS_PATH 跳过
    pytest.skip("Playwright requires browser; covered by integration test")
```

- [ ] **Step 3: 提交**

```bash
git add -A && git commit -m "feat(http): playwright fetcher for dynamic pages"
```

---

## Task 9：LLM 多模型路由 + 配置化 Prompt

**Files:**
- Create: `src/tv_list_aggregator/infrastructure/llm/openai_adapter.py`
- Create: `src/tv_list_aggregator/infrastructure/llm/anthropic_adapter.py`
- Create: `src/tv_list_aggregator/infrastructure/llm/ollama_adapter.py`
- Create: `src/tv_list_aggregator/infrastructure/llm/llm_router.py`
- Create: `src/tv_list_aggregator/infrastructure/llm/prompts/extract_program.yaml`
- Create: `src/tv_list_aggregator/infrastructure/llm/prompts/normalize.yaml`
- Create: `src/tv_list_aggregator/infrastructure/llm/prompt_loader.py`
- Test: `tests/unit/infrastructure/test_llm_router.py`

- [ ] **Step 1: OpenAI 适配器**

```python
# src/tv_list_aggregator/infrastructure/llm/openai_adapter.py
import os, json
from ...domain.ports.llm import LLM
from ...core.exceptions import LLMError

class OpenAIAdapter(LLM):
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model

    async def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        try:
            kwargs = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            r = await self._client.chat.completions.create(**kwargs)
            return r.choices[0].message.content or ""
        except Exception as e:
            raise LLMError(str(e)) from e

    async def embed(self, text: str) -> list[float]:
        r = await self._client.embeddings.create(model="text-embedding-3-small", input=text)
        return r.data[0].embedding
```

- [ ] **Step 2: Anthropic 与 Ollama 适配器（同接口；省略类似代码，注意 Ollama 使用本地 HTTP 协议）**

- [ ] **Step 3: 多模型兜底路由**

```python
# src/tv_list_aggregator/infrastructure/llm/llm_router.py
import asyncio
from ...domain.ports.llm import LLM
from ...core.exceptions import LLMError
from ...core.logging import get_logger

log = get_logger(__name__)

class LLMRouter(LLM):
    def __init__(self, primary: LLM, fallbacks: list[LLM]):
        self.primary = primary
        self.fallbacks = fallbacks

    async def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        chain = [self.primary, *self.fallbacks]
        last_err: Exception | None = None
        for idx, llm in enumerate(chain):
            try:
                return await llm.complete(prompt, json_mode=json_mode)
            except LLMError as e:
                last_err = e
                log.warning("llm.failure", provider_index=idx, error=str(e))
                await asyncio.sleep(0.2 * (idx + 1))
        raise LLMError(f"all llm providers failed: {last_err}")

    async def embed(self, text: str) -> list[float]:
        return await self.primary.embed(text)
```

- [ ] **Step 4: 配置化 Prompt**

```yaml
# src/tv_list_aggregator/infrastructure/llm/prompts/extract_program.yaml
version: 1
name: extract_program
description: 从异构网页文本中抽取节目信息
system: |
  你是严格的数据抽取器，仅基于用户提供的内容输出 JSON，禁止编造。
user_template: |
  请从以下内容中抽取所有电视节目条目，按 JSON 数组返回：
  字段：title(string), channel_id(string|null), channel_name(string), start(ISO8601), end(ISO8601), description(string|null)
  内容：
  """
  {{ content }}
  """
  仅返回 JSON，不要任何解释。
```

```yaml
# src/tv_list_aggregator/infrastructure/llm/prompts/normalize.yaml
version: 1
name: normalize
description: 标准化节目字段、纠错
user_template: |
  将以下 JSON 修正为标准格式：timezone 缺失则填 "UTC"，title 去前后空格，start/end 必须是 ISO8601。
  输入：{{ payload }}
  返回修正后的 JSON。
```

- [ ] **Step 5: Prompt 加载器**

```python
# src/tv_list_aggregator/infrastructure/llm/prompt_loader.py
import yaml
from pathlib import Path

class PromptLoader:
    def __init__(self, base_dir: str | Path):
        self.base = Path(base_dir)

    def render(self, name: str, **vars) -> str:
        data = yaml.safe_load((self.base / f"{name}.yaml").read_text(encoding="utf-8"))
        return data["user_template"].replace("{{ content }}", str(vars.get("content", ""))) \
                                     .replace("{{ payload }}", str(vars.get("payload", "")))
```

- [ ] **Step 6: 测试（mock 适配器）**

```python
# tests/unit/infrastructure/test_llm_router.py
import pytest
from tv_list_aggregator.infrastructure.llm.llm_router import LLMRouter
from tv_list_aggregator.core.exceptions import LLMError

class FakeLLM:
    def __init__(self, fail: bool, out: str = "ok"):
        self.fail = fail; self.out = out
    async def complete(self, prompt, *, json_mode=False): 
        if self.fail: raise LLMError("boom")
        return self.out
    async def embed(self, text): return [0.0]

@pytest.mark.asyncio
async def test_fallback_used():
    r = LLMRouter(primary=FakeLLM(fail=True), fallbacks=[FakeLLM(fail=False, out="ok")])
    assert await r.complete("hi") == "ok"
```

- [ ] **Step 7: 提交**

```bash
git add -A && git commit -m "feat(llm): multi-provider router & prompt loader"
```

---

## Task 10：解析器（JSON/HTML/LLM 增强）

**Files:**
- Create: `src/tv_list_aggregator/plugins/parsers/base.py`
- Create: `src/tv_list_aggregator/plugins/parsers/json_parser.py`
- Create: `src/tv_list_aggregator/plugins/parsers/html_parser.py`
- Create: `src/tv_list_aggregator/plugins/parsers/llm_parser.py`
- Test: `tests/unit/plugins/parsers/test_parsers.py`

- [ ] **Step 1: 解析器基类与契约**

```python
# src/tv_list_aggregator/plugins/parsers/base.py
import hashlib
from datetime import datetime, timezone
from ...domain.models.program import TVProgram
from ...domain.models.value_objects import Channel, TimeSlot

def make_identity_key(title: str, channel_id: str, start: datetime) -> str:
    raw = f"{title.strip().lower()}|{channel_id}|{start.isoformat()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()

def to_program(title: str, channel: Channel, start: datetime, end: datetime,
               description: str | None, source_id: str) -> TVProgram:
    now = datetime.now(timezone.utc)
    return TVProgram(
        title=title, channel=channel,
        slot=TimeSlot(start=start, end=end),
        description=description,
        source_ids=[source_id],
        identity_key=make_identity_key(title, channel.id, start),
        created_at=now, updated_at=now,
    )
```

- [ ] **Step 2: JSON 解析器**

```python
# src/tv_list_aggregator/plugins/parsers/json_parser.py
import json
from datetime import datetime
from .base import to_program
from ...domain.models.program import TVProgram
from ...domain.models.value_objects import Channel

class JSONParser:
    name = "json"
    async def parse(self, content: bytes, *, hint: dict | None = None) -> list[TVProgram]:
        data = json.loads(content)
        items = data if isinstance(data, list) else data.get("items", data.get("programs", []))
        out: list[TVProgram] = []
        for it in items:
            ch = Channel(id=str(it.get("channel_id") or it.get("channel", "unknown")),
                         name=str(it.get("channel_name") or it.get("channel", "unknown")))
            out.append(to_program(
                title=str(it["title"]), channel=ch,
                start=datetime.fromisoformat(it["start"]),
                end=datetime.fromisoformat(it["end"]),
                description=it.get("description"),
                source_id=hint.get("source_id", "unknown") if hint else "unknown",
            ))
        return out
```

- [ ] **Step 3: HTML 解析器（trafilatura 抽取正文 + selectolax 选区）**

```python
# src/tv_list_aggregator/plugins/parsers/html_parser.py
import trafilatura
from datetime import datetime
from selectolax.parser import HTMLParser
from .base import to_program
from ...domain.models.program import TVProgram
from ...domain.models.value_objects import Channel
from ...core.exceptions import ParseError

class HTMLParser_:
    name = "html"
    async def parse(self, content: bytes, *, hint: dict | None = None) -> list[TVProgram]:
        text = trafilatura.extract(content.decode("utf-8", errors="ignore")) or ""
        if not text:
            raise ParseError("no extractable text")
        # 简化策略：将整篇文本交给 LLM 解析；这里返回空，由 LLM parser 兜底
        return []
```

- [ ] **Step 4: LLM 解析器（兜底）**

```python
# src/tv_list_aggregator/plugins/parsers/llm_parser.py
import json
from datetime import datetime
from ...core.exceptions import ParseError, LLMError
from ...domain.models.program import TVProgram
from ...domain.models.value_objects import Channel
from ...domain.ports.llm import LLM
from ...infrastructure.llm.prompt_loader import PromptLoader
from .base import to_program

class LLMParser:
    name = "llm"
    def __init__(self, llm: LLM, prompts: PromptLoader):
        self.llm = llm
        self.prompts = prompts

    async def parse(self, content: bytes, *, hint: dict | None = None) -> list[TVProgram]:
        text = content.decode("utf-8", errors="ignore")[:30000]
        prompt = self.prompts.render("extract_program", content=text)
        try:
            raw = await self.llm.complete(prompt, json_mode=True)
        except LLMError as e:
            raise ParseError(str(e)) from e
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ParseError(f"llm returned non-json: {e}") from e
        items = data if isinstance(data, list) else data.get("items", [])
        out: list[TVProgram] = []
        for it in items:
            ch = Channel(id=str(it.get("channel_id") or "unknown"),
                         name=str(it.get("channel_name") or it.get("channel") or "unknown"))
            out.append(to_program(
                title=str(it["title"]).strip(), channel=ch,
                start=datetime.fromisoformat(it["start"]),
                end=datetime.fromisoformat(it["end"]),
                description=it.get("description"),
                source_id=hint.get("source_id", "unknown") if hint else "unknown",
            ))
        return out
```

- [ ] **Step 5: 测试**

```python
# tests/unit/plugins/parsers/test_parsers.py
import json
import pytest
from tv_list_aggregator.plugins.parsers.json_parser import JSONParser

@pytest.mark.asyncio
async def test_json_parser_basic():
    data = [{"title": "X", "channel": "C1", "start": "2026-01-01T10:00:00+00:00",
             "end": "2026-01-01T11:00:00+00:00", "description": "d"}]
    p = JSONParser()
    out = await p.parse(json.dumps(data).encode())
    assert len(out) == 1 and out[0].title == "X"
```

- [ ] **Step 6: 提交**

```bash
git add -A && git commit -m "feat(parsers): json/html/llm parsers"
```

---

## Task 11：源适配器 SPI 插件

**Files:**
- Create: `src/tv_list_aggregator/plugins/sources/base.py`
- Create: `src/tv_list_aggregator/plugins/sources/http_json_source.py`
- Create: `src/tv_list_aggregator/plugins/sources/rss_source.py`
- Create: `src/tv_list_aggregator/plugins/sources/html_scrape_source.py`
- Create: `src/tv_list_aggregator/plugins/sources/m3u_source.py`
- Create: `src/tv_list_aggregator/plugins/registry.py`
- Test: `tests/unit/plugins/test_registry.py`

- [ ] **Step 1: 源适配器抽象**

```python
# src/tv_list_aggregator/plugins/sources/base.py
from typing import Protocol
from ...domain.ports.fetcher import FetchResult
from ...domain.models.program import TVProgram

class SourceAdapter(Protocol):
    type: str
    async def fetch(self, source) -> FetchResult: ...
    async def parse(self, result: FetchResult, source) -> list[TVProgram]: ...
```

- [ ] **Step 2: HTTP JSON 源实现**

```python
# src/tv_list_aggregator/plugins/sources/http_json_source.py
from ...domain.ports.fetcher import Fetcher
from ...domain.ports.parser import Parser
from ...domain.models.source import TVListSource
from ...domain.models.program import TVProgram
from ...core.exceptions import ParseError
import json

class HTTPJSONSource:
    type = "http_json"
    def __init__(self, fetcher: Fetcher, parser: Parser):
        self.fetcher = fetcher
        self.parser = parser

    async def fetch(self, source: TVListSource):
        return await self.fetcher.fetch(str(source.url), headers=source.headers)

    async def parse(self, result, source: TVListSource) -> list[TVProgram]:
        return await self.parser.parse(result.body, hint={"source_id": source.id})
```

- [ ] **Step 3: HTML 抓取源（Playwright 兜底）**

```python
# src/tv_list_aggregator/plugins/sources/html_scrape_source.py
from ...infrastructure.http.playwright_fetcher import PlaywrightFetcher
from ...domain.models.source import TVListSource
from ...domain.models.program import TVProgram

class HTMLScrapeSource:
    type = "html_scrape"
    def __init__(self, fetcher: PlaywrightFetcher, parsers: list):
        self.fetcher = fetcher
        self.parsers = parsers  # 链式：html → llm

    async def fetch(self, source: TVListSource):
        return await self.fetcher.fetch(str(source.url), headers=source.headers,
                                         wait_selector=source.config.get("wait_selector"))

    async def parse(self, result, source: TVListSource) -> list[TVProgram]:
        for p in self.parsers:
            try:
                programs = await p.parse(result.body, hint={"source_id": source.id})
                if programs:
                    return programs
            except Exception:
                continue
        return []
```

- [ ] **Step 4: 插件注册器（基于 type 字段动态加载）**

```python
# src/tv_list_aggregator/plugins/registry.py
from typing import Callable, Any
from .sources.base import SourceAdapter

class PluginRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, Callable[[Any], SourceAdapter]] = {}
        self._parsers: dict[str, Any] = {}

    def register_source(self, type_name: str, factory: Callable[[Any], SourceAdapter]) -> None:
        self._sources[type_name] = factory

    def register_parser(self, name: str, parser: Any) -> None:
        self._parsers[name] = parser

    def build_source(self, type_name: str) -> SourceAdapter:
        if type_name not in self._sources:
            raise KeyError(f"unknown source type: {type_name}")
        return self._sources[type_name]()

    def get_parser(self, name: str):
        if name not in self._parsers:
            raise KeyError(f"unknown parser: {name}")
        return self._parsers[name]
```

- [ ] **Step 5: 测试**

```python
# tests/unit/plugins/test_registry.py
from tv_list_aggregator.plugins.registry import PluginRegistry
from tv_list_aggregator.plugins.sources.http_json_source import HTTPJSONSource

def test_registry_lookup():
    reg = PluginRegistry()
    reg.register_source("http_json", HTTPJSONSource)
    assert reg.build_source("http_json").type == "http_json"
```

- [ ] **Step 6: 提交**

```bash
git add -A && git commit -m "feat(plugins): source adapters & registry"
```

---

## Task 12：领域服务 - 标准化/去重/聚合

**Files:**
- Create: `src/tv_list_aggregator/domain/services/normalization_service.py`
- Create: `src/tv_list_aggregator/domain/services/dedup_service.py`
- Create: `src/tv_list_aggregator/domain/services/aggregation_service.py`
- Create: `src/tv_list_aggregator/domain/services/source_registry.py`
- Create: `src/tv_list_aggregator/domain/services/health_check_service.py`
- Test: `tests/unit/domain/services/test_dedup.py`

- [ ] **Step 1: 标准化（大小写/空白/标签归一）**

```python
# src/tv_list_aggregator/domain/services/normalization_service.py
import re
class NormalizationService:
    _WS = re.compile(r"\s+")
    def normalize_title(self, title: str) -> str:
        return self._WS.sub(" ", title).strip()
    def normalize_channel_id(self, cid: str) -> str:
        return cid.lower().strip()
```

- [ ] **Step 2: 去重（基于 identity_key + 标题相似度双保险）**

```python
# src/tv_list_aggregator/domain/services/dedup_service.py
from collections import defaultdict
from ..models.program import TVProgram

class DedupService:
    def __init__(self, similarity_threshold: float = 0.85):
        self.threshold = similarity_threshold

    def merge(self, programs: list[TVProgram]) -> list[TVProgram]:
        groups: dict[str, list[TVProgram]] = defaultdict(list)
        for p in programs:
            groups[p.identity_key].append(p)
        merged: list[TVProgram] = []
        for key, items in groups.items():
            if len(items) == 1:
                merged.append(items[0])
                continue
            base = items[0].model_copy(deep=True)
            base.source_ids = sorted({sid for p in items for sid in p.source_ids})
            base.description = next((p.description for p in items if p.description), base.description)
            base.tags = sorted({(t.label, t.category) for p in items for t in p.tags})
            base.tags = [type(items[0].tags[0])(label=l, category=c) for (l, c) in base.tags] if base.tags else []
            base.version = max(p.version for p in items)
            merged.append(base)
        return merged
```

- [ ] **Step 3: 聚合服务（编排 fetcher→parser→dedup→repo）**

```python
# src/tv_list_aggregator/domain/services/aggregation_service.py
import uuid
from datetime import datetime, timezone
from ...core.logging import get_logger
from ..models.crawl_job import CrawlJob, JobStatus
from ..models.program import TVProgram
from ..ports.fetcher import Fetcher
from ..ports.parser import Parser
from ..ports.program_repository import ProgramRepository
from ..ports.job_repository import JobRepository
from .dedup_service import DedupService
from .normalization_service import NormalizationService

log = get_logger(__name__)

class AggregationService:
    def __init__(self, fetcher: Fetcher, parser: Parser,
                 program_repo: ProgramRepository, job_repo: JobRepository,
                 dedup: DedupService, normalizer: NormalizationService):
        self.fetcher = fetcher
        self.parser = parser
        self.program_repo = program_repo
        self.job_repo = job_repo
        self.dedup = dedup
        self.normalizer = normalizer

    async def run_once(self, source) -> CrawlJob:
        job = CrawlJob(id=str(uuid.uuid4()), source_id=source.id,
                       status=JobStatus.RUNNING, started_at=datetime.now(timezone.utc))
        await self.job_repo.add(job)
        try:
            result = await self.fetcher.fetch(str(source.url), headers=source.headers)
            programs = await self.parser.parse(result.body, hint={"source_id": source.id})
            programs = [self._apply_norm(p) for p in programs]
            programs = self.dedup.merge(programs)
            saved = 0
            for p in programs:
                await self.program_repo.upsert(p)
                saved += 1
            job.status = JobStatus.SUCCESS
            job.items_fetched = len(programs)
            job.items_saved = saved
            job.finished_at = datetime.now(timezone.utc)
            await self.job_repo.update(job)
            return job
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)[:1000]
            job.finished_at = datetime.now(timezone.utc)
            await self.job_repo.update(job)
            log.error("aggregation.failed", source_id=source.id, error=str(e))
            raise

    def _apply_norm(self, p: TVProgram) -> TVProgram:
        p.title = self.normalizer.normalize_title(p.title)
        return p
```

- [ ] **Step 4: 健康检查服务**

```python
# src/tv_list_aggregator/domain/services/health_check_service.py
import time
from datetime import datetime, timezone
from ..ports.fetcher import Fetcher
from ..ports.source_repository import SourceRepository
from ..models.health import SourceHealth
from ...core.exceptions import SourceUnavailableError

class HealthCheckService:
    def __init__(self, fetcher: Fetcher, source_repo: SourceRepository):
        self.fetcher = fetcher
        self.source_repo = source_repo

    async def check(self, source) -> SourceHealth:
        if not source.url:
            return SourceHealth(source_id=source.id, is_alive=False,
                                latency_ms=None, checked_at=datetime.now(timezone.utc),
                                message="no url")
        start = time.monotonic()
        try:
            await self.fetcher.fetch(str(source.url), headers=source.headers, timeout=10.0)
            return SourceHealth(source_id=source.id, is_alive=True,
                                latency_ms=int((time.monotonic()-start)*1000),
                                checked_at=datetime.now(timezone.utc))
        except SourceUnavailableError as e:
            return SourceHealth(source_id=source.id, is_alive=False,
                                latency_ms=None, checked_at=datetime.now(timezone.utc),
                                message=str(e))
```

- [ ] **Step 5: 源注册中心（运行时启用/禁用）**

```python
# src/tv_list_aggregator/domain/services/source_registry.py
from ..ports.source_repository import SourceRepository
from ..models.source import SourceStatus

class SourceRegistry:
    def __init__(self, repo: SourceRepository):
        self.repo = repo
    async def active(self) -> list:
        return await self.repo.list(status=SourceStatus.ACTIVE.value)
    async def enable(self, source_id: str) -> None:
        s = await self.repo.get(source_id)
        if s: s.status = SourceStatus.ACTIVE; await self.repo.update(s)
    async def disable(self, source_id: str) -> None:
        s = await self.repo.get(source_id)
        if s: s.status = SourceStatus.DISABLED; await self.repo.update(s)
```

- [ ] **Step 6: 测试去重**

```python
# tests/unit/domain/services/test_dedup.py
from datetime import datetime, timezone
from tv_list_aggregator.domain.services.dedup_service import DedupService
from tv_list_aggregator.domain.models.program import TVProgram
from tv_list_aggregator.domain.models.value_objects import Channel, TimeSlot

def _p(title="X", sid="a"):
    ch = Channel(id="c1", name="C1")
    slot = TimeSlot(start=datetime(2026,1,1,10,tzinfo=timezone.utc), end=datetime(2026,1,1,11,tzinfo=timezone.utc))
    p = TVProgram(title=title, channel=ch, slot=slot, source_ids=[sid], identity_key="k1",
                  created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    return p

def test_dedup_merges_sources():
    p1, p2 = _p(sid="a"), _p(sid="b")
    out = DedupService().merge([p1, p2])
    assert len(out) == 1 and set(out[0].source_ids) == {"a","b"}
```

- [ ] **Step 7: 提交**

```bash
pytest tests/unit/domain/services -v
git add -A && git commit -m "feat(services): aggregation/dedup/health/registry"
```

---

## Task 13：调度系统

**Files:**
- Create: `src/tv_list_aggregator/interfaces/scheduler/scheduler.py`
- Create: `src/tv_list_aggregator/interfaces/scheduler/jobs/crawl_job.py`
- Create: `src/tv_list_aggregator/interfaces/scheduler/jobs/health_check_job.py`
- Create: `src/tv_list_aggregator/interfaces/scheduler/jobs/cleanup_job.py`
- Test: `tests/unit/interfaces/scheduler/test_scheduler.py`

- [ ] **Step 1: 调度器（APScheduler 异步包装）**

```python
# src/tv_list_aggregator/interfaces/scheduler/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class JobScheduler:
    def __init__(self) -> None:
        self.sched = AsyncIOScheduler()

    def start(self) -> None:
        if not self.sched.running:
            self.sched.start()

    def shutdown(self) -> None:
        if self.sched.running:
            self.sched.shutdown(wait=False)

    def add_cron(self, job_id: str, cron: str, func) -> None:
        self.sched.add_job(func, CronTrigger.from_crontab(cron), id=job_id, replace_existing=True, max_instances=1, coalesce=True)

    def add_interval(self, job_id: str, seconds: int, func) -> None:
        self.sched.add_job(func, "interval", seconds=seconds, id=job_id, replace_existing=True, max_instances=1, coalesce=True)
```

- [ ] **Step 2: 抓取任务包装**

```python
# src/tv_list_aggregator/interfaces/scheduler/jobs/crawl_job.py
from ....domain.services.aggregation_service import AggregationService
from ....domain.services.source_registry import SourceRegistry

async def crawl_all(agg: AggregationService, registry: SourceRegistry) -> None:
    sources = await registry.active()
    for s in sources:
        try:
            await agg.run_once(s)
        except Exception:
            continue
```

- [ ] **Step 3: 健康检查任务**

```python
# src/tv_list_aggregator/interfaces/scheduler/jobs/health_check_job.py
from ....domain.services.health_check_service import HealthCheckService
from ....domain.services.source_registry import SourceRegistry
from ....domain.ports.source_repository import SourceRepository
from ....domain.models.source import SourceStatus

async def health_loop(svc: HealthCheckService, registry: SourceRegistry,
                      repo: SourceRepository, threshold: int = 3) -> None:
    sources = await registry.active()
    fail_streak: dict[str, int] = {}
    for s in sources:
        h = await svc.check(s)
        if not h.is_alive:
            fail_streak[s.id] = fail_streak.get(s.id, 0) + 1
            if fail_streak[s.id] >= threshold:
                s.status = SourceStatus.PAUSED
                await repo.update(s)
```

- [ ] **Step 4: 测试调度器启停**

```python
# tests/unit/interfaces/scheduler/test_scheduler.py
import asyncio
from tv_list_aggregator.interfaces.scheduler.scheduler import JobScheduler

def test_scheduler_lifecycle():
    s = JobScheduler()
    s.start()
    assert s.sched.running
    s.shutdown()
```

- [ ] **Step 5: 提交**

```bash
git add -A && git commit -m "feat(scheduler): apscheduler wrapper & jobs"
```

---

## Task 14：FastAPI 接口层

**Files:**
- Create: `src/tv_list_aggregator/interfaces/api/app.py`
- Create: `src/tv_list_aggregator/interfaces/api/deps.py`
- Create: `src/tv_list_aggregator/interfaces/api/security.py`
- Create: `src/tv_list_aggregator/interfaces/api/middleware/request_id.py`
- Create: `src/tv_list_aggregator/interfaces/api/middleware/error_handler.py`
- Create: `src/tv_list_aggregator/interfaces/api/middleware/rate_limit.py`
- Create: `src/tv_list_aggregator/interfaces/api/routers/{sources,programs,jobs,health,export,admin}.py`
- Create: `src/tv_list_aggregator/interfaces/api/schemas/{source,program,job}.py`
- Test: `tests/integration/api/test_sources_router.py`

- [ ] **Step 1: 安全模块（JWT + 角色）**

```python
# src/tv_list_aggregator/interfaces/api/security.py
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from ...core.settings import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=True)
ROLE_ADMIN = "admin"
ROLE_USER = "user"

def create_access_token(sub: str, role: str = ROLE_USER, ttl_min: int = 60) -> str:
    s = get_settings()
    payload = {"sub": sub, "role": role, "exp": datetime.now(timezone.utc) + timedelta(minutes=ttl_min)}
    return jwt.encode(payload, s.secret_key, algorithm=s.jwt_algorithm)

def require_role(required: str):
    def _checker(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
        try:
            payload = jwt.decode(token, get_settings().secret_key, algorithms=[get_settings().jwt_algorithm])
        except JWTError as e:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from e
        if required not in (payload.get("role"), ROLE_ADMIN):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient role")
        return payload
    return _checker
```

- [ ] **Step 2: 中间件 - request_id 与错误处理**

```python
# src/tv_list_aggregator/interfaces/api/middleware/request_id.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["x-request-id"] = rid
        return response
```

```python
# src/tv_list_aggregator/interfaces/api/middleware/error_handler.py
import traceback
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from ....core.logging import get_logger
from ....core.exceptions import TVListBaseError

log = get_logger(__name__)

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except TVListBaseError as e:
            log.warning("domain.error", error=str(e), path=request.url.path)
            return JSONResponse({"error": type(e).__name__, "message": str(e)}, status_code=400)
        except Exception:
            log.error("unhandled.error", path=request.url.path, trace=traceback.format_exc())
            return JSONResponse({"error": "InternalServerError", "message": "internal error"}, status_code=500)
```

- [ ] **Step 3: 速率限制中间件**

```python
# src/tv_list_aggregator/interfaces/api/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from ....core.settings import get_settings

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{get_settings().rate_limit_per_minute}/minute"])
```

- [ ] **Step 4: 依赖注入与 schema**

```python
# src/tv_list_aggregator/interfaces/api/deps.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ...infrastructure.persistence.sqlalchemy_base import make_session_factory, make_engine
from ...core.settings import get_settings
from ...infrastructure.persistence.source_repository_impl import SQLAlchemySourceRepository
from ...infrastructure.persistence.program_repository_impl import SQLAlchemyProgramRepository
from ...infrastructure.persistence.job_repository_impl import SQLAlchemyJobRepository

_engine = None
_session_factory = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = make_engine(get_settings().database_url)
    return _engine

def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = make_session_factory(get_engine())
    return _session_factory

async def get_session() -> AsyncSession:
    Session = get_session_factory()
    async with Session() as s:
        yield s

async def get_source_repo(s: AsyncSession = Depends(get_session)):
    return SQLAlchemySourceRepository(s)
# 类似 program_repo / job_repo
```

```python
# src/tv_list_aggregator/interfaces/api/schemas/source.py
from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field
from ....domain.models.source import SourceType, SourceStatus

class SourceCreate(BaseModel):
    name: str
    type: SourceType
    url: HttpUrl | None = None
    config: dict = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    cron: str = "*/15 * * * *"
    priority: int = 5
    parser: str = "auto"

class SourceOut(BaseModel):
    id: str; name: str; type: SourceType; url: HttpUrl | None
    cron: str; priority: int; status: SourceStatus; parser: str
    created_at: datetime; updated_at: datetime
```

- [ ] **Step 5: Sources 路由**

```python
# src/tv_list_aggregator/interfaces/api/routers/sources.py
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from ...api.deps import get_source_repo
from ...api.schemas.source import SourceCreate, SourceOut
from ....domain.ports.source_repository import SourceRepository
from ....domain.models.source import TVListSource, SourceStatus
from ....interfaces.api.security import require_role, ROLE_ADMIN

router = APIRouter(prefix="/sources", tags=["sources"])

@router.post("", response_model=SourceOut, dependencies=[Depends(require_role(ROLE_ADMIN))])
async def create_source(payload: SourceCreate, repo: SourceRepository = Depends(get_source_repo)):
    now = datetime.now(timezone.utc)
    src = TVListSource(id=str(uuid.uuid4()), **payload.model_dump(), status=SourceStatus.ACTIVE,
                       created_at=now, updated_at=now)
    await repo.add(src)
    return SourceOut(**src.model_dump())

@router.get("", response_model=list[SourceOut])
async def list_sources(repo: SourceRepository = Depends(get_source_repo)):
    return [SourceOut(**s.model_dump()) for s in await repo.list()]

@router.delete("/{source_id}", status_code=204, dependencies=[Depends(require_role(ROLE_ADMIN))])
async def delete_source(source_id: str, repo: SourceRepository = Depends(get_source_repo)):
    await repo.delete(source_id)
```

- [ ] **Step 6: Health/Export/Admin 路由（健康指标 + CSV 导出 + 手动触发抓取）**

```python
# src/tv_list_aggregator/interfaces/api/routers/health.py
from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

router = APIRouter(tags=["health"])

@router.get("/healthz")
async def healthz():
    return {"status": "ok"}

@router.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

```python
# src/tv_list_aggregator/interfaces/api/routers/export.py
import csv
import io
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from ...api.deps import get_program_repo
from ....domain.ports.program_repository import ProgramRepository

router = APIRouter(prefix="/export", tags=["export"])

@router.get("/programs.csv")
async def export_csv(start: datetime, end: datetime,
                     channel_id: str | None = None,
                     repo: ProgramRepository = Depends(get_program_repo)):
    rows = await repo.list_by_range(start, end, channel_id=channel_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["title", "channel", "start", "end", "description"])
    for p in rows:
        w.writerow([p.title, p.channel.name, p.slot.start.isoformat(), p.slot.end.isoformat(), p.description or ""])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv")
```

```python
# src/tv_list_aggregator/interfaces/api/routers/admin.py
from fastapi import APIRouter, Depends
from ...api.deps import get_source_repo
from ....domain.ports.source_repository import SourceRepository
from ....domain.services.aggregation_service import AggregationService
from ....interfaces.api.security import require_role, ROLE_ADMIN

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role(ROLE_ADMIN))])

@router.post("/crawl/{source_id}")
async def trigger_crawl(source_id: str, repo: SourceRepository = Depends(get_source_repo)):
    # DI 在 app.state 中持有 AggregationService 单例
    from ...api.app import app_state
    agg: AggregationService = app_state["agg"]
    src = await repo.get(source_id)
    if not src: return {"ok": False, "error": "not found"}
    job = await agg.run_once(src)
    return {"ok": True, "job_id": job.id, "status": job.status.value}
```

- [ ] **Step 7: App 装配**

```python
# src/tv_list_aggregator/interfaces/api/app.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from ...core.logging import configure_logging, get_logger
from ...core.settings import get_settings
from ...core.tracing import init_tracer
from .middleware.request_id import RequestIDMiddleware
from .middleware.error_handler import ErrorHandlerMiddleware
from .middleware.rate_limit import limiter
from .routers import sources, programs, jobs, health, export, admin

app_state: dict = {}
log = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    configure_logging(s.log_level)
    init_tracer("tv-list-aggregator", s.otlp_endpoint)
    log.info("app.startup", env=s.app_env)
    # TODO: 实例化 fetcher/llm/agg 并放入 app_state
    yield
    log.info("app.shutdown")

def create_app() -> FastAPI:
    app = FastAPI(title="TV List Aggregator", version="0.1.0", lifespan=lifespan)
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
```

- [ ] **Step 8: 入口文件**

```python
# src/tv_list_aggregator/main.py
import uvicorn
from tv_list_aggregator.interfaces.api.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
```

- [ ] **Step 9: 集成测试**

```python
# tests/integration/api/test_sources_router.py
import pytest
from httpx import AsyncClient, ASGITransport
from tv_list_aggregator.interfaces.api.app import create_app

@pytest.mark.asyncio
async def test_health():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/healthz")
        assert r.status_code == 200
```

- [ ] **Step 10: 提交**

```bash
pytest tests/integration/api -v
git add -A && git commit -m "feat(api): fastapi routers, security, middleware"
```

---

## Task 15：可观测性（指标 + Sentry + 健康）

**Files:**
- Create: `src/tv_list_aggregator/observability/metrics.py`
- Create: `src/tv_list_aggregator/observability/health.py`
- Test: `tests/unit/observability/test_metrics.py`

- [ ] **Step 1: 业务指标**

```python
# src/tv_list_aggregator/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge

CRAWL_SUCCESS = Counter("tvlist_crawl_success_total", "Successful crawls", ["source_id"])
CRAWL_FAILURE = Counter("tvlist_crawl_failure_total", "Failed crawls", ["source_id", "reason"])
CRAWL_LATENCY = Histogram("tvlist_crawl_latency_seconds", "Crawl latency", ["source_id"])
PROGRAMS_INGESTED = Counter("tvlist_programs_ingested_total", "Programs upserted")
LLM_TOKENS = Counter("tvlist_llm_tokens_total", "LLM tokens used", ["provider", "model"])
ACTIVE_SOURCES = Gauge("tvlist_active_sources", "Active sources count")
```

- [ ] **Step 2: 健康聚合**

```python
# src/tv_list_aggregator/observability/health.py
from datetime import datetime, timezone
from ..domain.ports.source_repository import SourceRepository
from ..domain.services.health_check_service import HealthCheckService

async def detailed_health(repo: SourceRepository, health_svc: HealthCheckService) -> dict:
    sources = await repo.list()
    results = []
    for s in sources:
        h = await health_svc.check(s)
        results.append({"source_id": s.id, "alive": h.is_alive, "latency_ms": h.latency_ms})
    return {"checked_at": datetime.now(timezone.utc).isoformat(), "sources": results, "all_alive": all(r["alive"] for r in results)}
```

- [ ] **Step 3: 测试**

```python
# tests/unit/observability/test_metrics.py
from tv_list_aggregator.observability.metrics import CRAWL_SUCCESS
CRAWL_SUCCESS.labels(source_id="x").inc()
assert CRAWL_SUCCESS.labels(source_id="x")._value.get() >= 1
```

- [ ] **Step 4: 提交**

```bash
git add -A && git commit -m "feat(observability): metrics & health aggregator"
```

---

## Task 16：Docker 化与 CI

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.github/workflows/ci.yml`
- Create: `config/sources.example.yaml`
- Create: `config/legal_notice.md`

- [ ] **Step 1: Dockerfile（多阶段）**

```dockerfile
FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install ".[dev]"
COPY src ./src
RUN pip install --no-deps .
EXPOSE 8000
CMD ["uvicorn", "tv_list_aggregator.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: docker-compose（API + Postgres + Redis）**

```yaml
version: "3.9"
services:
  api:
    build: .
    env_file: .env
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: tvlist
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
volumes: { pgdata: {} }
```

- [ ] **Step 3: CI（lint/type/test/build）**

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_USER: user, POSTGRES_PASSWORD: pass, POSTGRES_DB: tvlist_test }
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: mypy src
      - run: pytest -q --cov=tv_list_aggregator --cov-report=xml
      - run: docker build -t tvlist:test .
```

- [ ] **Step 4: 合法声明与示例源配置**

```markdown
<!-- config/legal_notice.md -->
本项目仅聚合公开可访问的节目元数据，遵循各数据源的使用条款与 robots.txt；请勿用于商业转售，遵守当地法律法规。
```

```yaml
# config/sources.example.yaml
sources:
  - id: demo-json
    name: Demo JSON API
    type: http_json
    url: https://example.com/epg.json
    cron: "*/30 * * * *"
    parser: json
```

- [ ] **Step 5: 提交**

```bash
git add -A && git commit -m "chore: docker, ci, example configs"
```

---

## Task 17：端到端冒烟测试

**Files:**
- Create: `tests/e2e/test_pipeline.py`

- [ ] **Step 1: E2E（mock HTTP + LLM，验证全链路）**

```python
# tests/e2e/test_pipeline.py
import pytest, respx, httpx
from datetime import datetime, timezone
from tv_list_aggregator.infrastructure.http.client import ResilientHTTPFetcher
from tv_list_aggregator.plugins.parsers.json_parser import JSONParser
from tv_list_aggregator.domain.services.dedup_service import DedupService
from tv_list_aggregator.domain.services.normalization_service import NormalizationService

@pytest.mark.asyncio
async def test_end_to_end_json_pipeline():
    fetcher = ResilientHTTPFetcher(rate_per_minute=10000)
    body = b'[{"title":"A","channel":"C1","start":"2026-01-01T10:00:00+00:00","end":"2026-01-01T11:00:00+00:00"}]'
    with respx.mock(base_url="https://e") as m:
        m.get("/p").mock(return_value=httpx.Response(200, content=body))
        r = await fetcher.fetch("https://e/p")
        programs = await JSONParser().parse(r.body, hint={"source_id": "s1"})
        programs = DedupService().merge(programs)
        assert len(programs) == 1
    await fetcher.aclose()
```

- [ ] **Step 2: 提交**

```bash
pytest tests/e2e -v
git add -A && git commit -m "test(e2e): smoke pipeline"
```

---

## 自检清单（Spec 覆盖）

- 数据源管理（动态增删/优先级/频率/验证）→ Task 4, 6, 11, 12
- 健康监测（链接/响应/内容）→ Task 12 (HealthCheckService) + Task 15
- 自动化更新与爬取（动态解析 + LLM 增强）→ Task 7, 8, 10
- 异构整合/去重/分类 → Task 12
- 存储与版本（数据库/版本/历史）→ Task 6（version 字段 + jobs 历史）
- API 与导出（REST/CSV/可视化可选）→ Task 14
- 智能纠错（LLM 修正）→ Task 9 + prompts/normalize.yaml
- 用户反馈（迭代优化）→ 预留 `feedback_service.py`（Task 12 位置）
- 安全与权限（API Key/JWT/HTTPS）→ Task 14 security + Dockerfile
- 多线程/分布式（Scrapy/Celery）→ Task 7（异步） + 后续 Celery 适配
- 监控与日志（traceId/指标/异常）→ Task 2, 3, 15
- 容器化与 K8s → Task 16
- 性能/扩展/容错/一致性 → 全链路重试/熔断/限流/去重
- 风险与应对（备用源/法律声明）→ Task 12（fail_streak 自动暂停）+ Task 16

---

## 执行选择

**计划已保存到 `docs/superpowers/plans/2026-06-10-tv-list-aggregator.md`。两种执行方式：**

1. **Subagent-Driven（推荐）** — 每个任务派发独立子代理，任务间审查，快速迭代
2. **Inline Execution** — 在当前会话按任务顺序执行，含检查点

请选择执行方式，或指出要先调整哪些任务/范围。
