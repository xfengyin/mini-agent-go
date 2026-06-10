"""开发期种子数据：让 GUI 在空库里也能展示真实形态。

设计原则：
- 幂等：重复调用不会重复插入（按 identity_key / id 去重）
- 仅 dev：production 模式下函数直接返回 no-op
- 可观测：每条插入都打 log
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ...core.logging import get_logger
from ...domain.models.crawl_job import JobStatus
from ...domain.models.source import SourceStatus, SourceType, TVListSource
from ...infrastructure.persistence.models import JobRow, ProgramRow, SourceRow

log = get_logger(__name__)


# 节目模板：分类 + 标题列表（用于随机化填充）
_PROGRAM_TITLES = {
    "drama": [
        "漫长的季节", "狂飙", "三体", "人世间", "梦华录",
        "繁花", "去有风的地方", "知否知否", "琅琊榜", "庆余年",
    ],
    "news": [
        "新闻联播", "东方时空", "焦点访谈", "新闻直播间", "国际时讯",
        "The World Today", "BBC News at Ten", "Sky News Tonight",
    ],
    "variety": [
        "奔跑吧", "歌手", "中国好声音", "向往的生活", "脱口秀大会",
        "Strictly Come Dancing", "The Voice UK", "Love Island",
    ],
    "movie": [
        "肖申克的救赎", "霸王别姬", "阿甘正传", "盗梦空间", "星际穿越",
        "The Dark Knight", "Inception", "Interstellar", "Pulp Fiction",
    ],
    "sports": [
        "NBA 总决赛", "欧冠决赛", "世界杯集锦", "英超第 38 轮", "中超联赛",
        "Premier League", "Champions League Final", "Wimbledon Highlights",
    ],
    "kids": [
        "汪汪队立大功", "小猪佩奇", "海底小纵队", "宝宝巴士", "超级飞侠",
        "Peppa Pig", "Paw Patrol", "Bluey", "Cocomelon",
    ],
    "doc": [
        "地球脉动", "舌尖上的中国", "河西走廊", "航拍中国", "蓝色星球",
        "Planet Earth", "Blue Planet II", "Our Planet", "Cosmos",
    ],
}


def _id(prefix: str = "") -> str:
    """生成稳定可读 ID。"""
    return f"{prefix}{uuid.uuid4().hex[:12]}" if prefix else uuid.uuid4().hex


def _build_sample_sources() -> list[TVListSource]:
    """构造 3 个示例数据源。"""
    now = datetime.now(tz=UTC)
    common = {
        "config": {},
        "headers": {},
        "cron": "*/15 * * * *",
        "priority": 5,
        "status": SourceStatus.ACTIVE,
        "parser": "auto",
        "created_at": now,
        "updated_at": now,
    }
    return [
        TVListSource(
            id="src_demo_iqiyi",
            name="iQIYI 热播剧场",
            type=SourceType.HTTP_JSON,
            url="https://demo.example.com/iqiyi/epg.json",
            **common,
        ),
        TVListSource(
            id="src_demo_cctv",
            name="CCTV 节目单",
            type=SourceType.RSS,
            url="https://demo.example.com/cctv/schedule.xml",
            **common,
        ),
        TVListSource(
            id="src_demo_iptv",
            name="示例 IPTV 列表",
            type=SourceType.M3U,
            url="https://demo.example.com/iptv/playlist.m3u",
            **common,
        ),
    ]


def _build_sample_programs(sources: list[TVListSource]) -> list[ProgramRow]:
    """为每个源生成 48 小时节目数据。"""
    now = datetime.now(tz=UTC)
    rows: list[ProgramRow] = []
    # 频道：每个源 4 个频道
    channel_defs: list[tuple[str, str, str]] = [
        # (channel_id, channel_name, category)
        ("ch_cctv1", "CCTV-1 综合", "news"),
        ("ch_cctv4", "CCTV-4 中文国际", "doc"),
        ("ch_zjjs", "浙江卫视", "drama"),
        ("ch_aqzws", "爱情·周末", "variety"),
        ("ch_bbc1", "BBC One", "drama"),
        ("ch_bbc2", "BBC Two", "doc"),
        ("ch_skynews", "Sky News", "news"),
        ("ch_skyarts", "Sky Arts", "variety"),
        ("ch_m3u_movie", "电影频道 HD", "movie"),
        ("ch_m3u_kids", "少儿动画", "kids"),
        ("ch_m3u_sport", "体育竞技", "sports"),
        ("ch_m3u_doc", "自然纪录", "doc"),
    ]

    # 把频道按 3 个源分组
    source_split = [
        sources[0].id,  # iQIYI
        sources[1].id,  # CCTV
        sources[2].id,  # IPTV
    ]

    for idx, (ch_id, ch_name, category) in enumerate(channel_defs):
        src_id = source_split[idx % len(source_split)]
        titles = _PROGRAM_TITLES[category]
        # 每频道生成 48 小时内 30 分钟 / 1 小时的节目
        start = now - timedelta(hours=2)
        slot_minutes = 30 if category in ("news", "kids", "sports") else 60
        slot_count = (48 * 60) // slot_minutes
        for i in range(slot_count):
            slot_start = start + timedelta(minutes=slot_minutes * i)
            slot_end = slot_start + timedelta(minutes=slot_minutes)
            title = titles[i % len(titles)]
            desc = f"《{title}》-{ch_name} 播出"
            identity = f"{ch_id}|{slot_start.isoformat()}"
            rows.append(
                ProgramRow(
                    id=_id("prog_"),
                    title=title,
                    description=desc,
                    channel_id=ch_id,
                    channel_name=ch_name,
                    channel_logo=None,
                    channel_country="CN" if ch_id.startswith("ch_") and not ch_id.startswith("ch_bbc") and not ch_id.startswith("ch_sky") else "GB",
                    channel_language="zh-CN" if idx < 8 else "en-GB",
                    start_at=slot_start,
                    end_at=slot_end,
                    timezone="UTC",
                    tags=[{"label": category, "category": "genre"}],
                    source_ids=[src_id],
                    identity_key=identity,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
            )
    return rows


def _build_sample_jobs(sources: list[TVListSource]) -> list[JobRow]:
    """构造 6 条历史任务。"""
    now = datetime.now(tz=UTC)
    job_specs = [
        # (source_idx, status, minutes_ago, fetched, saved, error)
        (0, JobStatus.SUCCESS, 5, 142, 138, None),
        (1, JobStatus.SUCCESS, 35, 96, 95, None),
        (2, JobStatus.SUCCESS, 65, 312, 310, None),
        (0, JobStatus.FAILED, 125, 0, 0, "connection timeout after 30s"),
        (2, JobStatus.SUCCESS, 180, 280, 278, None),
        (1, JobStatus.RUNNING, 0, 12, 0, None),
    ]
    rows: list[JobRow] = []
    for src_idx, status, mins_ago, fetched, saved, err in job_specs:
        started = now - timedelta(minutes=mins_ago)
        finished = None if status == JobStatus.RUNNING else started + timedelta(seconds=8)
        rows.append(
            JobRow(
                id=_id("job_"),
                source_id=sources[src_idx].id,
                status=status.value,
                started_at=started,
                finished_at=finished,
                items_fetched=fetched,
                items_saved=saved,
                error=err,
                trace_id=_id("tr_"),
            )
        )
    return rows


async def seed_if_empty(session_factory: async_sessionmaker[AsyncSession]) -> dict:
    """在空库中插入演示数据。返回写入统计。"""
    async with session_factory() as session:
        existing_sources = (await session.execute(select(SourceRow))).first()
        if existing_sources is not None:
            log.info("seed.skipped", reason="db not empty")
            return {"skipped": True, "reason": "db not empty"}

        sources = _build_sample_sources()
        programs = _build_sample_programs(sources)
        jobs = _build_sample_jobs(sources)

        for s in sources:
            session.add(
                SourceRow(
                    id=s.id,
                    name=s.name,
                    type=s.type.value,
                    url=str(s.url) if s.url else None,
                    config=s.config,
                    headers=s.headers,
                    cron=s.cron,
                    priority=s.priority,
                    status=s.status.value,
                    parser=s.parser,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                )
            )
        session.add_all(programs)
        session.add_all(jobs)
        await session.commit()

    log.info("seed.completed", sources=len(sources), programs=len(programs), jobs=len(jobs))
    return {
        "skipped": False,
        "sources": len(sources),
        "programs": len(programs),
        "jobs": len(jobs),
    }


async def reset_and_seed(session_factory: async_sessionmaker[AsyncSession]) -> dict:
    """清空 + 重新插入（dev 调试用）。"""
    async with session_factory() as session:
        for tbl in (ProgramRow, JobRow, SourceRow):
            await session.execute(tbl.__table__.delete())
        await session.commit()

    return await seed_if_empty(session_factory)
