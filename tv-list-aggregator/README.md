"""项目根 README。"""
# TV List Aggregator

多源 TV List 自动聚合 AI Agent。参考 [项目实施计划](docs/superpowers/plans/2026-06-10-tv-list-aggregator.md)。

## 特性

- 多源接入：HTTP JSON / RSS / HTML 抓取 / M3U（插件化 SPI）
- 智能解析：JSON → HTML → LLM 三段式
- LLM 兜底：OpenAI / Anthropic / Ollama / Stub
- 数据处理：标准化 + 去重 + 分类
- 高可用：限流 / 熔断 / 指数退避 / 自动暂停
- 可观测：结构化日志、Prometheus、OpenTelemetry
- 安全：JWT 角色、配置化密钥

## 快速开始

```bash
pip install -e ".[dev]"
cp .env.example .env  # 编辑配置
uvicorn tv_list_aggregator.main:app --reload
```

## 测试

```bash
pytest -q
```

## 部署

```bash
docker compose up -d
```

## 文档

- [架构设计](docs/architecture.md)
- [运维手册](docs/operations.md)
- [安全合规](docs/security.md)
