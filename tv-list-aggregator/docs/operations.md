# 运维手册

## 健康检查

- Liveness: `GET /healthz` → 进程存活
- Prometheus: `GET /metrics`
- 详细健康（应用内）：使用 `observability.health.detailed_health`

## 监控指标

| 指标 | 含义 |
|---|---|
| `tvlist_crawl_success_total` | 抓取成功计数（按源） |
| `tvlist_crawl_failure_total` | 抓取失败计数（按源/原因） |
| `tvlist_crawl_latency_seconds` | 抓取耗时直方图 |
| `tvlist_programs_ingested_total` | 入库节目数 |
| `tvlist_active_sources` | 活跃源数量 |

## 调度任务

| Job | 频率 | 用途 |
|---|---|---|
| `crawl_all_active` | 由源 cron 决定 | 抓取所有活跃源 |
| `health_check_loop` | 每 5 分钟 | 健康巡检，连续失败自动暂停 |
| `cleanup_old_jobs` | 每日 03:00 | 清理 30 天前任务 |

## 故障排查

- **源失败率高**：检查 `health_check_job` 的 fail_streak 日志
- **解析失败**：开启 LLM 兜底；调整 `prompts/extract_program.yaml`
- **DB 连接耗尽**：检查 `pool_pre_ping` / `pool_size`；必要时扩容

## 部署清单

- [ ] `SECRET_KEY` 替换为强随机值
- [ ] `OPENAI_API_KEY` 配置
- [ ] 启用 `ENABLE_TELEMETRY=true` + `OTLP_ENDPOINT`
- [ ] 配置日志聚合（Sentry / Loki / ELK）
- [ ] 反向代理（Nginx）启用 HTTPS
