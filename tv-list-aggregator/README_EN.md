<a id="lang-switch"></a>
# TV List Aggregator

> **🌐 Language / 语言:** [🇬🇧 English](#) · [🇨🇳 中文](./README.md)

---

## Overview

**TV List Aggregator** is a **production-grade, multi-source TV schedule aggregation AI agent**. Through an SPI plugin architecture, it ingests data from multiple sources (HTTP JSON / RSS / HTML scrape / M3U), uses LLM as a fallback for unstructured content, normalizes, deduplicates, and persists channel / program / time-slot data, and exposes a clean REST API.

## Key Features

- **Multi-source ingestion** — HTTP JSON, RSS, HTML scrape, M3U; plug-and-play SPI
- **Three-stage parsing** — JSON → HTML → LLM with graceful degradation
- **LLM fallback chain** — OpenAI / Anthropic / Ollama / Stub providers
- **Data processing** — title & channel-ID normalization, idempotent dedup by `identity_key`
- **High availability** — async circuit breaker (closed / open / half_open), token-bucket rate limit, exponential backoff, health-check auto-pause
- **Observability** — structlog, 6 Prometheus business metrics, optional OpenTelemetry
- **Security** — JWT + RBAC, slowapi rate limiting, configurable secrets
- **API** — FastAPI with auto OpenAPI, CSV streaming export, admin endpoints
- **Operations** — Docker / docker-compose, GitHub Actions CI, config-driven prompts & sources

## Architecture

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
│ abstractions│  │ Sources  │  │ LLM / Cache   │
└─────────────┘  └──────────┘  └────────────────┘
```

## Quick Start

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

## Configure Sources (YAML)

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

## Testing

```bash
# All tests
pytest -q

# With coverage
pytest --cov=tv_list_aggregator --cov-report=term-missing

# Single module
pytest tests/unit/domain/services/test_dedup.py -q
```

## Deployment

```bash
# Docker
docker compose up -d

# Or build standalone
docker build -t tv-list-aggregator:latest .
```

## Documentation

- [Architecture](docs/architecture.md)
- [Operations](docs/operations.md)
- [Security & Compliance](docs/security.md)
- [Implementation Plan](docs/superpowers/plans/2026-06-10-tv-list-aggregator.md)

## API Cheatsheet

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

## Security & Legal

This project aggregates **user-authorized or publicly available** schedule data. Before deploying, please read [config/legal_notice.md](config/legal_notice.md) and [docs/security.md](docs/security.md), and comply with local laws and the target sites' `robots.txt` and Terms of Service.

---

## License

Internal use — All rights reserved.

<p align="right"><a href="#lang-switch">⬆ Back to top</a> · <a href="./README.md">🇨🇳 切换到中文</a></p>
