# 架构设计

## 分层

```
┌──────────────────────────────────────────────────────────┐
│ Interfaces: FastAPI / APScheduler / CLI                  │
├──────────────────────────────────────────────────────────┤
│ Domain Services: Aggregation / Dedup / Normalization /   │
│                  HealthCheck / SourceRegistry            │
├──────────────────────────────────────────────────────────┤
│ Domain Models + Ports (Protocols)                        │
├──────────────────────────────────────────────────────────┤
│ Infrastructure: SQLAlchemy / httpx / Playwright /        │
│                OpenAI / Anthropic / Ollama / EventBus    │
├──────────────────────────────────────────────────────────┤
│ Plugins (SPI): sources/* parsers/*                       │
└──────────────────────────────────────────────────────────┘
```

## 关键决策

- **依赖倒置**：领域定义 Port（Protocol），基础设施实现 → 可替换存储/LLM/HTTP
- **SPI 插件**：按 `type` 字段动态加载源适配器，新增源零修改主流程
- **配置化 Prompt**：YAML 模板 + 占位符，零代码即可调整抽取规则
- **多 LLM 兜底**：主 provider 失败后顺序尝试 fallback，保证可用性
- **可观测贯穿**：所有层使用 structlog，Prometheus 业务指标，OpenTelemetry trace
- **熔断 + 限流**：HTTP 层令牌桶 + pybreaker，避免对源站造成压力

## 数据流

```
Source → Fetcher (httpx/Playwright) → Parser (json/html/llm)
  → NormalizationService → DedupService → ProgramRepository
  → AggregationService 记录 Job → API/Export
```
