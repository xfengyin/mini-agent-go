"""Port 接口契约测试。"""
from __future__ import annotations

from tv_list_aggregator.domain.ports.cache import Cache
from tv_list_aggregator.domain.ports.clock import Clock
from tv_list_aggregator.domain.ports.event_bus import EventBus
from tv_list_aggregator.domain.ports.fetcher import Fetcher
from tv_list_aggregator.domain.ports.job_repository import JobRepository
from tv_list_aggregator.domain.ports.llm import LLM
from tv_list_aggregator.domain.ports.parser import Parser
from tv_list_aggregator.domain.ports.program_repository import ProgramRepository
from tv_list_aggregator.domain.ports.source_repository import SourceRepository


def test_ports_have_required_methods() -> None:
    # 校验所有 Port 都暴露了必要的方法（接口隔离）
    assert hasattr(SourceRepository, "get")
    assert hasattr(ProgramRepository, "upsert")
    assert hasattr(JobRepository, "add")
    assert hasattr(Fetcher, "fetch")
    assert hasattr(Parser, "parse")
    assert hasattr(LLM, "complete")
    assert hasattr(Cache, "get")
    assert hasattr(EventBus, "publish")
    assert hasattr(Clock, "now")
