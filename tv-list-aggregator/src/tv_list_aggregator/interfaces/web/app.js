/* TVLIST GUI — 前端逻辑
 * 风格：vanilla JS + 静态文件 + 真实 API（带 mock fallback）
 * 路由：直接 fetch FastAPI /api/v1/* 端点
 */

(() => {
  "use strict";

  // ========== 状态 ==========
  const state = {
    view: "timeline",
    hours: 3,
    token: localStorage.getItem("tvlist_token") || null,
    data: { summary: null, timeline: null, topChannels: null },
    refreshTimer: null,
  };

  // ========== DOM ==========
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);
  const dom = {
    healthPct: $("#healthPct"),
    programsCount: $("#programsCount"),
    sourcesCount: $("#sourcesCount"),
    refreshBtn: $("#refreshBtn"),
    triggerCrawlBtn: $("#triggerCrawlBtn"),
    timelineSub: $("#timelineSub"),
    epgHours: $("#epgHours"),
    epgBody: $("#epgBody"),
    programsHint: $("#programsHint"),
    programsSub: $("#programsSub"),
    programGrid: $("#programGrid"),
    sourcesHint: $("#sourcesHint"),
    sourcesSub: $("#sourcesSub"),
    sourceList: $("#sourceList"),
    jobsHint: $("#jobsHint"),
    jobsSub: $("#jobsSub"),
    jobTable: $("#jobTable"),
    channelsSub: $("#channelsSub"),
    rankList: $("#rankList"),
    lastUpdated: $("#lastUpdated"),
    nowTime: $("#nowTime"),
    nowDate: $("#nowDate"),
    searchInput: $("#searchInput"),
    toastHost: $("#toastHost"),
  };

  // ========== 工具 ==========
  const fmt = {
    n: (v) => (v == null ? "—" : Number(v).toLocaleString()),
    pct: (v) => (v == null ? "—" : `${v}%`),
    time: (iso) => {
      if (!iso) return "—";
      const d = new Date(iso);
      return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
    },
    date: (iso) => {
      if (!iso) return "—";
      const d = new Date(iso);
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    },
    relative: (iso) => {
      if (!iso) return "—";
      const d = new Date(iso);
      const sec = Math.floor((Date.now() - d.getTime()) / 1000);
      if (sec < 60) return `${sec}s ago`;
      if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
      if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
      return `${Math.floor(sec / 86400)}d ago`;
    },
    initials: (s) =>
      (s || "?")
        .split(/[\s_-]+/)
        .map((p) => p[0])
        .filter(Boolean)
        .slice(0, 2)
        .join("")
        .toUpperCase(),
  };

  const api = async (path, opts = {}) => {
    const url = path.startsWith("http") ? path : `/api/v1${path}`;
    const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
    if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
    const r = await fetch(url, { ...opts, headers });
    if (!r.ok) {
      const text = await r.text();
      throw new Error(`${r.status} ${text.slice(0, 120)}`);
    }
    return r.json();
  };

  const toast = (msg, kind = "ok") => {
    const el = document.createElement("div");
    el.className = `toast toast--${kind}`;
    el.innerHTML = `<span class="toast__icon">${kind === "ok" ? "✓" : "✕"}</span><span>${msg}</span>`;
    dom.toastHost.appendChild(el);
    setTimeout(() => {
      el.style.transition = "opacity 0.3s, transform 0.3s";
      el.style.opacity = "0";
      el.style.transform = "translateX(20px)";
      setTimeout(() => el.remove(), 320);
    }, 3200);
  };

  // ========== 视图切换 ==========
  const switchView = (name) => {
    state.view = name;
    $$(".view").forEach((v) => v.classList.toggle("is-active", v.dataset.view === name));
    $$(".nav__item").forEach((n) => n.classList.toggle("is-active", n.dataset.view === name));
    loadView(name);
  };

  $$(".nav__item").forEach((n) => {
    n.addEventListener("click", () => switchView(n.dataset.view));
  });

  $$(".seg__btn").forEach((b) => {
    b.addEventListener("click", () => {
      $$(".seg__btn").forEach((x) => x.classList.remove("is-active"));
      b.classList.add("is-active");
      state.hours = Number(b.dataset.hours);
      loadTimeline();
    });
  });

  dom.refreshBtn.addEventListener("click", async () => {
    dom.refreshBtn.querySelector(".btn__icon").style.animation = "spin 0.6s linear";
    setTimeout(() => {
      dom.refreshBtn.querySelector(".btn__icon").style.animation = "";
    }, 600);
    await refreshAll();
    toast("数据已刷新", "ok");
  });

  dom.triggerCrawlBtn.addEventListener("click", async () => {
    try {
      dom.triggerCrawlBtn.disabled = true;
      dom.triggerCrawlBtn.style.opacity = "0.5";
      await api("/admin/crawl-all", { method: "POST" });
      toast("已触发全量抓取", "ok");
    } catch (e) {
      toast(`触发失败: ${e.message}`, "err");
    } finally {
      dom.triggerCrawlBtn.disabled = false;
      dom.triggerCrawlBtn.style.opacity = "";
    }
  });

  // 快捷键：/ 聚焦搜索
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement.tagName !== "INPUT") {
      e.preventDefault();
      dom.searchInput.focus();
    }
  });

  dom.searchInput.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase().trim();
    filterCurrentView(q);
  });

  // ========== 数据加载 ==========
  const loadView = (name) => {
    switch (name) {
      case "timeline": loadTimeline(); break;
      case "programs": loadPrograms(); break;
      case "sources": loadSources(); break;
      case "jobs": loadJobs(); break;
      case "channels": loadTopChannels(); break;
    }
  };

  const loadSummary = async () => {
    try {
      const s = await api("/dashboard/summary");
      state.data.summary = s;
      dom.healthPct.textContent =
        s.sources.total > 0 ? Math.round((s.sources.active / s.sources.total) * 100) : "—";
      dom.programsCount.textContent = fmt.n(s.programs.total);
      dom.sourcesCount.textContent = fmt.n(s.sources.total);
      dom.programsHint.textContent = fmt.n(s.programs.total);
      dom.sourcesHint.textContent = `${s.sources.active}/${s.sources.total}`;
      dom.jobsHint.textContent = Object.values(s.jobs.by_status).reduce((a, b) => a + b, 0);
      dom.lastUpdated.textContent = `${fmt.relative(s.generated_at)} · refreshed`;
    } catch (e) {
      console.warn("summary 加载失败", e);
    }
  };

  const loadTimeline = async () => {
    try {
      const t = await api(`/dashboard/timeline?hours=${state.hours}`);
      state.data.timeline = t;
      renderTimeline(t);
      dom.timelineSub.textContent = `${fmt.time(t.from)} → ${fmt.time(t.to)} · ${Object.keys(t.programs_by_channel).length} 频道`;
    } catch (e) {
      dom.epgBody.innerHTML = `<div class="epg__loading">⚠ ${e.message}</div>`;
    }
  };

  const renderTimeline = (data) => {
    // 渲染时间刻度
    const start = new Date(data.from);
    const end = new Date(data.to);
    const total = (end - start) / 1000 / 60; // minutes
    const hours = [];
    for (let h = 0; h <= state.hours; h++) {
      const t = new Date(start.getTime() + h * 3600 * 1000);
      hours.push(`<div class="epg__hour">${String(t.getHours()).padStart(2, "0")}:00</div>`);
    }
    dom.epgHours.innerHTML = hours.join("");

    // 渲染频道行
    const channels = Object.entries(data.programs_by_channel);
    if (channels.length === 0) {
      dom.epgBody.innerHTML = `<div class="epg__loading">暂无节目数据</div>`;
      return;
    }
    const nowPct = ((new Date(data.now) - start) / (end - start)) * 100;
    const html = channels
      .map(([channelName, programs]) => {
        const bars = programs
          .map((p) => {
            const pStart = new Date(p.start);
            const pEnd = new Date(p.end);
            const leftPct = Math.max(0, ((pStart - start) / (end - start)) * 100);
            const rightPct = Math.min(100, ((pEnd - start) / (end - start)) * 100);
            const widthPct = rightPct - leftPct;
            const isLive = pStart <= new Date(data.now) && pEnd >= new Date(data.now);
            return `<div class="epg-row__bar ${isLive ? "is-live" : ""}"
                         style="left:${leftPct}%;width:${widthPct}%"
                         title="${p.title} · ${fmt.time(p.start)}-${fmt.time(p.end)}">
                      <div class="epg-row__title">${escape(p.title)}</div>
                      <div class="epg-row__time">${fmt.time(p.start)} – ${fmt.time(p.end)}</div>
                    </div>`;
          })
          .join("");
        return `<div class="epg-row">
          <div class="epg-row__channel">
            <div class="epg-row__avatar">${fmt.initials(channelName)}</div>
            <div class="epg-row__name">${escape(channelName)}</div>
          </div>
          <div class="epg-row__track">${bars}</div>
        </div>`;
      })
      .join("");

    dom.epgBody.innerHTML = html + `<div class="now-line" style="left:calc(140px + ${nowPct}% * (100% - 140px) / 100)"></div>`;
  };

  const loadPrograms = async () => {
    try {
      const list = await api("/programs?limit=60");
      renderPrograms(list.items || list);
      dom.programsSub.textContent = `${(list.items || list).length} 条 · sorted by start time`;
    } catch (e) {
      dom.programGrid.innerHTML = `<div class="program-grid__loading">⚠ ${e.message}</div>`;
    }
  };

  const renderPrograms = (items) => {
    if (items.length === 0) {
      dom.programGrid.innerHTML = `<div class="program-grid__loading">暂无节目</div>`;
      return;
    }
    dom.programGrid.innerHTML = items
      .map(
        (p) => `<div class="program-card" data-q="${(p.title + " " + (p.channel_name || "")).toLowerCase()}">
        <div class="program-card__channel">${escape(p.channel_name || "—")}</div>
        <div class="program-card__title">${escape(p.title)}</div>
        <div class="program-card__time">
          <span>${fmt.date(p.start_at)}</span>
          <span class="program-card__dot"></span>
          <span>${fmt.time(p.start_at)} – ${fmt.time(p.end_at)}</span>
        </div>
      </div>`
      )
      .join("");
  };

  const loadSources = async () => {
    try {
      const list = await api("/sources");
      renderSources(list);
      dom.sourcesSub.textContent = `${list.length} 个数据源`;
    } catch (e) {
      dom.sourceList.innerHTML = `<div class="program-grid__loading">⚠ ${e.message}</div>`;
    }
  };

  const renderSources = (items) => {
    if (items.length === 0) {
      dom.sourceList.innerHTML = `<div class="program-grid__loading">暂无数据源</div>`;
      return;
    }
    dom.sourceList.innerHTML = items
      .map(
        (s) => `<div class="source-card" data-q="${(s.name + " " + (s.url || "")).toLowerCase()}">
        <div class="source-card__type">${escape(s.type)}</div>
        <div>
          <div class="source-card__name">${escape(s.name)}</div>
          <div class="source-card__url">${escape(s.url || "—")}</div>
        </div>
        <div class="source-card__cron">${escape(s.cron)}</div>
        <div class="source-card__status">
          <span class="dot dot--${s.status === "active" ? "ok" : "disabled"}"></span>
          ${s.status}
        </div>
      </div>`
      )
      .join("");
  };

  const loadJobs = async () => {
    try {
      // 后端不一定有 list-jobs，先尝试
      const list = await api("/admin/jobs?limit=20").catch(() => []);
      const data = state.data.summary?.jobs?.recent || list;
      renderJobs(data);
      dom.jobsSub.textContent = `最近 ${data.length} 条任务`;
    } catch (e) {
      dom.jobTable.innerHTML = `<div class="program-grid__loading">⚠ ${e.message}</div>`;
    }
  };

  const renderJobs = (items) => {
    if (items.length === 0) {
      dom.jobTable.innerHTML = `<div class="program-grid__loading">暂无任务</div>`;
      return;
    }
    const head = `<div class="job-row job-row--head">
      <div>id</div><div>source</div><div>status</div><div>started</div>
      <div>fetched</div><div>saved</div>
    </div>`;
    const rows = items
      .map(
        (j) => `<div class="job-row">
        <div class="job-id">${escape((j.id || "").slice(0, 12))}</div>
        <div>${escape(j.source_id || "—")}</div>
        <div><span class="job-status job-status--${j.status}">
          <span class="dot"></span>${j.status}
        </span></div>
        <div class="job-time">${fmt.relative(j.started_at)}</div>
        <div class="job-cnt">${fmt.n(j.items_fetched)}</div>
        <div class="job-cnt">${fmt.n(j.items_saved)}</div>
      </div>`
      )
      .join("");
    dom.jobTable.innerHTML = head + rows;
  };

  const loadTopChannels = async () => {
    try {
      const data = await api("/dashboard/top-channels?limit=10");
      state.data.topChannels = data;
      renderTopChannels(data);
      dom.channelsSub.textContent = `节目数 Top ${data.items.length}`;
    } catch (e) {
      dom.rankList.innerHTML = `<li class="program-grid__loading">⚠ ${e.message}</li>`;
    }
  };

  const renderTopChannels = (data) => {
    if (!data.items || data.items.length === 0) {
      dom.rankList.innerHTML = `<li class="program-grid__loading">暂无频道</li>`;
      return;
    }
    const max = Math.max(...data.items.map((c) => c.program_count));
    dom.rankList.innerHTML = data.items
      .map(
        (c) => `<li class="rank-item">
        <div class="rank-item__avatar">${fmt.initials(c.channel_name)}</div>
        <div class="rank-item__name">${escape(c.channel_name)}</div>
        <div class="rank-item__bar">
          <div class="rank-item__bar-fill" style="width:${(c.program_count / max) * 100}%"></div>
        </div>
        <div class="rank-item__cnt">${fmt.n(c.program_count)}</div>
      </li>`
      )
      .join("");
  };

  // ========== 搜索过滤 ==========
  const filterCurrentView = (q) => {
    if (!q) {
      $$(`[data-q]`).forEach((el) => (el.style.display = ""));
      return;
    }
    $$(`[data-q]`).forEach((el) => {
      el.style.display = el.dataset.q.includes(q) ? "" : "none";
    });
  };

  const escape = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ========== 全量刷新 ==========
  const refreshAll = async () => {
    await loadSummary();
    if (state.view === "timeline") await loadTimeline();
    else if (state.view === "programs") await loadPrograms();
    else if (state.view === "sources") await loadSources();
    else if (state.view === "jobs") await loadJobs();
    else if (state.view === "channels") await loadTopChannels();
  };

  // ========== Tick 时钟 ==========
  const tickClock = () => {
    const d = new Date();
    dom.nowTime.textContent = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}:${String(d.getSeconds()).padStart(2, "0")}`;
    dom.nowDate.textContent = `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
  };

  // ========== 启动 ==========
  const start = async () => {
    tickClock();
    setInterval(tickClock, 1000);
    await refreshAll();
    // 每 30 秒自动刷新 summary（timeline 自己每分钟刷）
    state.refreshTimer = setInterval(async () => {
      await loadSummary();
      if (state.view === "timeline") await loadTimeline();
    }, 30_000);
  };

  // 暴露给 e2e 测试
  window.__tvlist = { switchView, state, refreshAll };

  document.addEventListener("DOMContentLoaded", start);
})();
