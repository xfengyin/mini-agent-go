# TV List Aggregator

> 企业级多源 TV List 自动聚合 AI Agent
> Enterprise-grade multi-source TV list aggregation AI agent.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-Internal-lightgrey)](#)
[![Tests](https://img.shields.io/badge/tests-36%20passed-brightgreen)](./tests)

---

## 🇨🇳 中文说明

### 项目简介

TV List Aggregator 是一个**生产可用的多源电视节目表聚合 AI Agent**，通过 SPI 插件化架构接入多种数据源（HTTP JSON / RSS / HTML 抓取 / M3U），借助 LLM 智能兜底解析，实现频道、节目单、时段的标准化、去重与持久化，并通过 REST API 对外提供能力。

### 核心特性

- **多源接入**：HTTP JSON / RSS / HTML Scrape / M3U，SPI 插件化即插即用
- **智能解析**：JSON → HTML → LLM 三段式，渐进式降级
- **LLM 兜底**：支持 OpenAI / Anthropic / Ollama / Stub 多 Provider 链式 fallback
- **数据处理**：标题归一化、频道 ID 归一化、基于 `identity_key` 的幂等去重
- **高可用**：异步熔断器（closed / open / half_open 三态机）+ 令牌桶限流 + 指数退避 + 健康检查自动暂停
- **可观测**：structlog 结构化日志、Prometheus 业务指标（6 项）、可选 OpenTelemetry
- **安全合规**：JWT + RBAC、slowapi 速率限制、配置化密钥
- **接口完备**：FastAPI 自动 OpenAPI、CSV 流式导出、Admin 端点
- **运维友好**：Docker / docker-compose、GitHub Actions CI、可配置化提示词与源定义

### 架构概览

```
┌──────────────────────────────────────────────────────────────┐
│                      FastAPI 接口层                          │
│   (routers / middleware / JWT / RateLimit / OpenAPI)        │
└──────────────┬───────────────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────────────┐
│                   领域服务层（Domain）                        │
│  normalize │ dedup │ aggregate │ health │ registry │ feedback │
└──────┬───────┴──────┬─────────┴────┬──────────────────────────┘
       │              │             │
┌──────▼──────┐  ┌────▼─────┐  ┌─────▼──────────┐
│ Ports (SPI) │  │ Plugins  │  │ Infrastructure│
│ 9 Protocols │  │ Parsers  │  │ HTTP / DB /   │
│ 抽象接口     │  │ Sources  │  │ LLM / Cache   │
└─────────────┘  └──────────┘  └────────────────┘
```

### 快速开始

```bash
# 1. 安装依赖
pip install -e ".[dev]"

# 2. 复制并编辑环境变量
cp .env.example .env

# 3. 启动服务
uvicorn tv_list_aggregator.main:app --reload --port 8000

# 4. 打开浏览器
#    Swagger UI: http://localhost:8000/docs
#    Health:     http://localhost:8000/healthz
#    Metrics:    http://localhost:8000/metrics
```

### 配置源（YAML）

编辑 `config/sources.yaml`（参考 [config/sources.example.yaml](config/sources.example.yaml)）：

```yaml
sources:
  - id: cctv
    name: CCTV 节目单
    type: http_json
    url: https://example.com/cctv.json
    cron: "*/15 * * * *"
    parser: json

  - id: m3u-demo
    name: M3U 演示
    type: m3u
    url: https://example.com/playlist.m3u
    cron: "0 */1 * * *"
    parser: json
```

### 测试

```bash
# 运行所有测试
pytest -q

# 带覆盖率
pytest --cov=tv_list_aggregator --cov-report=term-missing

# 单个模块
pytest tests/unit/domain/services/test_dedup.py -q
```

### 部署

```bash
# Docker 一键启动
docker compose up -d

# 单独构建
docker build -t tv-list-aggregator:latest .
```

### 文档导航

- [架构设计](docs/architecture.md)
- [运维手册](docs/operations.md)
- [安全合规](docs/security.md)
- [实施计划](docs/superpowers/plans/2026-06-10-tv-list-aggregator.md)

### API 速览

| Method | Path | 说明 |
|---|---|---|
| `GET`  | `/healthz` | 健康检查 |
| `GET`  | `/metrics` | Prometheus 指标 |
| `GET`  | `/api/v1/sources` | 列出源 |
| `POST` | `/api/v1/sources` | 创建源 |
| `GET`  | `/api/v1/programs?channel=...&date=...` | 检索节目 |
| `GET`  | `/api/v1/jobs` | 任务列表 |
| `GET`  | `/api/v1/export/programs.csv` | CSV 导出 |
| `POST` | `/api/v1/admin/crawl/{source_id}` | 手动触发抓取 |

### 安全与法律

本项目用于**聚合用户授权或公开的节目单数据**。请在部署前阅读 [config/legal_notice.md](config/legal_notice.md) 与 [docs/security.md](docs/security.md)，并遵守当地法律法规及目标站点的 `robots.txt` 与服务条款。

---

## 🇬🇧 English

### Overview

**TV List Aggregator** is a **production-grade, multi-source TV schedule aggregation AI agent**. Through an SPI plugin architecture, it ingests data from multiple sources (HTTP JSON / RSS / HTML scrape / M3U), uses LLM as a fallback for unstructured content, normalizes, deduplicates, and persists channel / program / time-slot data, and exposes a clean REST API.

### Key Features

- **Multi-source ingestion** — HTTP JSON, RSS, HTML scrape, M3U; plug-and-play SPI
- **Three-stage parsing** — JSON → HTML → LLM with graceful degradation
- **LLM fallback chain** — OpenAI / Anthropic / Ollama / Stub providers
- **Data processing** — title & channel-ID normalization, idempotent dedup by `identity_key`
- **High availability** — async circuit breaker (closed / open / half_open), token-bucket rate limit, exponential backoff, health-check auto-pause
- **Observability** — structlog, 6 Prometheus business metrics, optional OpenTelemetry
- **Security** — JWT + RBAC, slowapi rate limiting, configurable secrets
- **API** — FastAPI with auto OpenAPI, CSV streaming export, admin endpoints
- **Operations** — Docker / docker-compose, GitHub Actions CI, config-driven prompts & sources

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       FastAPI Layer                          │
│    (routers / middleware / JWT / RateLimit / OpenAPI)       │
└──────────────┬───────────────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────────────┐
│                    Domain Services                           │
│  normalize │ dedup │ aggregate │ health │ registry │ feedback │
└──────┬───────┴──────┬─────────┴────┬──────────────────────────┘
       │              │             │
┌──────▼──────┐  ┌────▼─────┐  ┌─────▼──────────┐
│ Ports (SPI) │  │ Plugins  │  │ Infrastructure│
│ 9 Protocols │  │ Parsers  │  │ HTTP / DB /   │
│  abstractions│  │ Sources  │  │ LLM / Cache   │
└─────────────┘  └──────────┘  └────────────────┘
```

### Quick Start

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env

# 3. Run
uvicorn tv_list_aggregator.main:app --reload --port 8000

# 4. Open
#    Swagger UI: http://localhost:8000/docs
#    Health:     http://localhost:8000/healthz
#    Metrics:    http://localhost:8000/metrics
```

### Configure Sources (YAML)

Edit `config/sources.yaml` (see [config/sources.example.yaml](config/sources.example.yaml)):

```yaml
sources:
  - id: cctv
    name: CCTV schedule
    type: http_json
    url: https://example.com/cctv.json
    cron: "*/15 * * * *"
    parser: json

  - id: m3u-demo
    name: M3U demo
    type: m3u
    url: https://example.com/playlist.m3u
    cron: "0 */1 * * *"
    parser: json
```

### Testing

```bash
# All tests
pytest -q

# With coverage
pytest --cov=tv_list_aggregator --cov-report=term-missing

# Single module
pytest tests/unit/domain/services/test_dedup.py -q
```

### Deployment

```bash
# Docker
docker compose up -d

# Or build standalone
docker build -t tv-list-aggregator:latest .
```

### Documentation

- [Architecture](docs/architecture.md)
- [Operations](docs/operations.md)
- [Security & Compliance](docs/security.md)
- [Implementation Plan](docs/superpowers/plans/2026-06-10-tv-list-aggregator.md)

### API Cheatsheet

| Method | Path | Description |
|---|---|---|
| `GET`  | `/healthz` | Health check |
| `GET`  | `/metrics` | Prometheus metrics |
| `GET`  | `/api/v1/sources` | List sources |
| `POST` | `/api/v1/sources` | Create source |
| `GET`  | `/api/v1/programs?channel=...&date=...` | Query programs |
| `GET`  | `/api/v1/jobs` | Job list |
| `GET`  | `/api/v1/export/programs.csv` | CSV export |
| `POST` | `/api/v1/admin/crawl/{source_id}` | Trigger crawl |

### Security & Legal

This project aggregates **user-authorized or publicly available** schedule data. Before deploying, please read [config/legal_notice.md](config/legal_notice.md) and [docs/security.md](docs/security.md), and comply with local laws and the target sites' `robots.txt` and Terms of Service.

---

## License / 许可

Internal / 内部使用 — All rights reserved.
