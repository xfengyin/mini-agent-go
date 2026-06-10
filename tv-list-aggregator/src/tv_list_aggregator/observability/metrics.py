"""Prometheus 业务指标。"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# 抓取成功/失败
CRAWL_SUCCESS = Counter(
    "tvlist_crawl_success_total", "Successful crawls", ["source_id"]
)
CRAWL_FAILURE = Counter(
    "tvlist_crawl_failure_total", "Failed crawls", ["source_id", "reason"]
)
CRAWL_LATENCY = Histogram(
    "tvlist_crawl_latency_seconds", "Crawl latency in seconds", ["source_id"]
)

# 节目入库
PROGRAMS_INGESTED = Counter(
    "tvlist_programs_ingested_total", "Programs successfully upserted"
)

# LLM 统计
LLM_TOKENS = Counter(
    "tvlist_llm_tokens_total", "LLM tokens used", ["provider", "model"]
)

# 活跃源
ACTIVE_SOURCES = Gauge("tvlist_active_sources", "Number of active sources")
