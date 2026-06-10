/* =====================================================
 * TVLIST IDE — 前端逻辑
 * 资源浏览器（Cursor 风格）：活动栏 / 资源树 / Tab / 详情 / 编辑
 * 单文件 vanilla JS，无依赖；通过 /static/app.js 加载。
 * ===================================================== */

(() => {
  "use strict";

  // ============== 状态 ==============
  const state = {
    token: localStorage.getItem("tvlist_token") || null,
    user: null, // {username, role} 解码自 JWT
    activity: "sources",
    tabs: [],        // [{id, type, itemId, title, dirty, content}]
    activeTabId: null,
    explorer: { sources: [], channels: [], jobs: [], programs: [], plugins: [] },
    filter: "",
    contextNode: null, // {type, id}
  };

  // ============== DOM 引用 ==============
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));
  const dom = {
    topbar: $("#topbar"),
    cmdPalette: $("#cmdPalette"),
    envPill: $("#envPill"),
    accountMenu: $("#accountMenu"),
    accountBtn: $("#accountBtn"),
    accountName: $("#accountName"),
    accountDropdown: $("#accountDropdown"),
    accountInfoUser: $("#accountInfoUser"),
    accountInfoRole: $("#accountInfoRole"),
    accountInfoToken: $("#accountInfoToken"),
    accountAction: $("#accountAction"),
    activityBar: $("#activityBar"),
    explorerBody: $("#explorerBody"),
    explorerSearch: $("#explorerSearch"),
    explorerRefresh: $("#explorerRefresh"),
    tabBar: $("#tabBar"),
    tabContent: $("#tabContent"),
    panelTabs: $("#panelTabs"),
    panelContent: $("#panelContent"),
    statusEnv: $("#statusEnv"),
    statusDb: $("#statusDb"),
    statusToken: $("#statusToken"),
    statusPath: $("#statusPath"),
    statusClock: $("#statusClock"),
    statusSynced: $("#statusSynced"),
    loginOverlay: $("#loginOverlay"),
    loginForm: $("#loginForm"),
    loginUser: $("#loginUser"),
    loginPass: $("#loginPass"),
    loginError: $("#loginError"),
    loginSubmit: $("#loginSubmit"),
    toastHost: $("#toastHost"),
    contextMenu: $("#contextMenu"),
    crawlBtn: $("#crawlBtn"),
  };

  // ============== 工具函数 ==============
  const escape = (s) =>
    String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");

  const fmtDate = (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleString("zh-CN", { hour12: false });
  };

  const fmtTime = (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleTimeString("zh-CN", { hour12: false });
  };

  const debounce = (fn, ms = 200) => {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  };

  const decodeJwt = (token) => {
    try {
      const part = token.split(".")[1];
      const padded = part + "=".repeat((4 - (part.length % 4)) % 4);
      const payload = atob(padded.replace(/-/g, "+").replace(/_/g, "/"));
      return JSON.parse(payload);
    } catch {
      return null;
    }
  };

  // ============== API ==============
  const api = async (path, opts = {}) => {
    const headers = { Accept: "application/json", ...(opts.headers || {}) };
    if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
    if (opts.body && typeof opts.body === "object" && !(opts.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.body);
    }
    const res = await fetch(path, { ...opts, headers });
    if (!res.ok) {
      let err = `HTTP ${res.status}`;
      try {
        const data = await res.json();
        err = data.detail || data.title || err;
        if (data.request_id) err += ` [${data.request_id.slice(0, 8)}]`;
      } catch {}
      const e = new Error(err);
      e.status = res.status;
      throw e;
    }
    if (res.status === 204) return null;
    return res.json();
  };

  // ============== Toast ==============
  const toast = (title, body = "", kind = "info", timeout = 3000) => {
    const el = document.createElement("div");
    el.className = `toast toast--${kind}`;
    el.innerHTML = `<div class="toast__title">${escape(title)}</div>${body ? `<div class="toast__body">${escape(body)}</div>` : ""}`;
    dom.toastHost.appendChild(el);
    setTimeout(() => {
      el.style.transition = "opacity 0.3s, transform 0.3s";
      el.style.opacity = "0";
      el.style.transform = "translateX(20px)";
      setTimeout(() => el.remove(), 300);
    }, timeout);
  };

  // ============== 认证 ==============
  const showLogin = () => {
    dom.loginOverlay.hidden = false;
    setTimeout(() => dom.loginUser.focus(), 50);
  };

  const hideLogin = () => {
    dom.loginOverlay.hidden = true;
    dom.loginError.hidden = true;
  };

  const updateAccount = () => {
    if (state.token) {
      const payload = decodeJwt(state.token);
      state.user = payload
        ? { username: payload.sub || "user", role: payload.role || "user" }
        : { username: "user", role: "user" };
      dom.accountName.textContent = state.user.username;
      dom.accountMenu.classList.add("is-authed");
      dom.accountInfoUser.textContent = state.user.username;
      dom.accountInfoRole.textContent = state.user.role;
      dom.accountInfoToken.textContent = state.token.slice(0, 12) + "…";
      dom.accountAction.textContent = "退出登录";
      dom.statusToken.textContent = `🔓 ${state.user.username}/${state.user.role}`;
    } else {
      state.user = null;
      dom.accountName.textContent = "未登录";
      dom.accountMenu.classList.remove("is-authed");
      dom.accountInfoUser.textContent = "—";
      dom.accountInfoRole.textContent = "—";
      dom.accountInfoToken.textContent = "—";
      dom.accountAction.textContent = "登录";
      dom.statusToken.textContent = "🔒 unauth";
    }
  };

  const doLogin = async (username, password) => {
    try {
      dom.loginSubmit.disabled = true;
      const res = await api("/api/v1/auth/token", {
        method: "POST",
        body: new URLSearchParams({ username, password }),
      });
      state.token = res.access_token;
      localStorage.setItem("tvlist_token", state.token);
      hideLogin();
      updateAccount();
      toast("登录成功", state.token.slice(0, 12) + "…", "ok");
      await refreshAll();
    } catch (e) {
      dom.loginError.textContent = e.message;
      dom.loginError.hidden = false;
    } finally {
      dom.loginSubmit.disabled = false;
    }
  };

  const doLogout = () => {
    state.token = null;
    localStorage.removeItem("tvlist_token");
    updateAccount();
    showLogin();
    toast("已退出登录", "", "info", 2000);
  };

  // ============== 活动栏 ==============
  const switchActivity = (root) => {
    state.activity = root;
    $$(".activity-btn").forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.activity === root);
    });
    loadExplorer(root);
  };

  // ============== 资源树 ==============
  const loadExplorer = async (root) => {
    try {
      if (root === "sources") {
        const list = await api("/api/v1/sources");
        state.explorer.sources = list;
      } else if (root === "channels") {
        const list = await api("/api/v1/channels");
        state.explorer.channels = list;
      } else if (root === "jobs") {
        const list = await api("/api/v1/jobs?limit=100");
        state.explorer.jobs = list;
      } else if (root === "programs") {
        const end = new Date();
        const start = new Date(end.getTime() - 24 * 3600 * 1000);
        const list = await api(
          `/api/v1/programs?start=${encodeURIComponent(start.toISOString())}&end=${encodeURIComponent(end.toISOString())}`
        );
        state.explorer.programs = (list || []).slice(0, 200);
      } else if (root === "plugins") {
        const list = await api("/api/v1/admin/plugins");
        state.explorer.plugins = [
          ...list.source_types.map((t) => ({ kind: "source_type", id: t, name: t })),
          ...list.parsers.map((p) => ({ kind: "parser", id: p, name: p })),
        ];
      }
    } catch (e) {
      toast("加载失败", e.message, "err");
    }
    renderExplorer();
  };

  const renderExplorer = () => {
    const filter = state.filter.trim().toLowerCase();
    const match = (s) => !filter || (s || "").toLowerCase().includes(filter);

    // sources
    {
      const ul = $("#tree-sources");
      const items = state.explorer.sources.filter((s) => match(s.name) || match(s.id));
      $("#cnt-sources").textContent = items.length;
      ul.innerHTML = items
        .map(
          (s) => `
        <li class="tree-node ${s.status === "active" ? "is-status-active" : "is-status-disabled"}" data-type="source" data-id="${escape(s.id)}" data-status="${escape(s.status)}">
          <span class="tree-node__icon">${s.status === "active" ? "●" : "○"}</span>
          <span class="tree-node__label">${escape(s.name)}</span>
          <span class="tree-node__sub">${escape(s.type)}</span>
        </li>`
        )
        .join("");
    }
    // channels
    {
      const ul = $("#tree-channels");
      const items = state.explorer.channels.filter((c) => match(c.channel_name) || match(c.channel_id));
      $("#cnt-channels").textContent = items.length;
      ul.innerHTML = items
        .slice(0, 200)
        .map(
          (c) => `
        <li class="tree-node" data-type="channel" data-id="${escape(c.channel_id)}">
          <span class="tree-node__icon">📺</span>
          <span class="tree-node__label">${escape(c.channel_name)}</span>
          <span class="tree-node__sub">${c.program_count}</span>
        </li>`
        )
        .join("");
    }
    // jobs
    {
      const ul = $("#tree-jobs");
      const items = state.explorer.jobs.filter((j) => match(j.id) || match(j.source_id));
      $("#cnt-jobs").textContent = items.length;
      ul.innerHTML = items
        .slice(0, 100)
        .map(
          (j) => `
        <li class="tree-node is-status-${j.status}" data-type="job" data-id="${escape(j.id)}">
          <span class="tree-node__icon">${statusIcon(j.status)}</span>
          <span class="tree-node__label">${escape(j.id.slice(0, 14))}…</span>
          <span class="tree-node__sub">${escape(j.source_id.slice(0, 10))}</span>
        </li>`
        )
        .join("");
    }
    // programs
    {
      const ul = $("#tree-programs");
      const items = state.explorer.programs.filter(
        (p) => match(p.title) || match(p.channel_name)
      );
      $("#cnt-programs").textContent = items.length;
      ul.innerHTML = items
        .slice(0, 150)
        .map(
          (p) => `
        <li class="tree-node" data-type="program" data-id="${escape(p.id)}">
          <span class="tree-node__icon">▷</span>
          <span class="tree-node__label">${escape(p.title)}</span>
          <span class="tree-node__sub">${escape(p.channel_name || "—")}</span>
        </li>`
        )
        .join("");
    }
    // plugins
    {
      const ul = $("#tree-plugins");
      const items = state.explorer.plugins.filter((p) => match(p.name));
      $("#cnt-plugins").textContent = items.length;
      ul.innerHTML = items
        .map(
          (p) => `
        <li class="tree-node" data-type="plugin" data-id="${escape(p.id)}">
          <span class="tree-node__icon">${p.kind === "source_type" ? "ⓘ" : "§"}</span>
          <span class="tree-node__label">${escape(p.name)}</span>
          <span class="tree-node__sub">${escape(p.kind)}</span>
        </li>`
        )
        .join("");
    }
  };

  const statusIcon = (s) => {
    return { success: "✓", failed: "✗", running: "◐", pending: "○" }[s] || "·";
  };

  // ============== Tab 系统 ==============
  const newTabId = () => "tab_" + Math.random().toString(36).slice(2, 10);

  const openTab = async (type, itemId, title) => {
    let tab = state.tabs.find((t) => t.type === type && t.itemId === itemId);
    if (!tab) {
      tab = {
        id: newTabId(),
        type,
        itemId,
        title: title || `${type}:${itemId}`,
        dirty: false,
        content: null,
        panelTab: "overview",
        original: null,
      };
      state.tabs.push(tab);
    }
    state.activeTabId = tab.id;
    renderTabs();
    await loadTabContent(tab);
    renderTabs();
    renderTabContent(tab);
  };

  const closeTab = (tabId) => {
    const idx = state.tabs.findIndex((t) => t.id === tabId);
    if (idx < 0) return;
    state.tabs.splice(idx, 1);
    if (state.activeTabId === tabId) {
      state.activeTabId = state.tabs[idx]?.id || state.tabs[idx - 1]?.id || null;
    }
    renderTabs();
    if (state.activeTabId) {
      const t = state.tabs.find((x) => x.id === state.activeTabId);
      renderTabContent(t);
    } else {
      dom.tabContent.innerHTML = `<div class="welcome">
        <div class="welcome__brand">▦ TVLIST IDE</div>
        <h1 class="welcome__title">资源浏览器</h1>
        <p class="welcome__sub">从左侧选择资源类型开始浏览</p>
      </div>`;
      dom.panelTabs.innerHTML = "";
      dom.panelContent.innerHTML = `<div class="panel-empty">选中资源以查看详情</div>`;
    }
  };

  const switchTab = (tabId) => {
    state.activeTabId = tabId;
    const t = state.tabs.find((x) => x.id === tabId);
    if (t) {
      renderTabs();
      renderTabContent(t);
    }
  };

  const renderTabs = () => {
    dom.tabBar.innerHTML = state.tabs
      .map(
        (t) => `
      <div class="tab ${t.id === state.activeTabId ? "is-active" : ""}" data-tab="${t.id}">
        <span class="tab__icon">${tabIcon(t.type)}</span>
        <span class="tab__title">${escape(t.title)}</span>
        <span class="tab__dirty" ${t.dirty ? "" : "hidden"}></span>
        <button class="tab__close" data-close="${t.id}">×</button>
      </div>`
      )
      .join("");
    // 状态：选中节点路径
    const active = state.tabs.find((t) => t.id === state.activeTabId);
    if (active) {
      dom.statusPath.textContent = `${active.type} / ${active.itemId}`;
    } else {
      dom.statusPath.textContent = "—";
    }
  };

  const tabIcon = (type) => ({ source: "ⓘ", channel: "📺", job: "▤", program: "▦", plugin: "⚙" })[type] || "·";

  const loadTabContent = async (tab) => {
    try {
      if (tab.type === "source") {
        const data = await api(`/api/v1/sources/${tab.itemId}`);
        tab.original = data;
        tab.content = data;
      } else if (tab.type === "channel") {
        const ch = state.explorer.channels.find((c) => c.channel_id === tab.itemId);
        tab.original = ch;
        tab.content = ch;
      } else if (tab.type === "job") {
        const j = state.explorer.jobs.find((x) => x.id === tab.itemId);
        tab.original = j;
        tab.content = j;
      } else if (tab.type === "program") {
        const p = state.explorer.programs.find((x) => x.id === tab.itemId);
        tab.original = p;
        tab.content = p;
      } else if (tab.type === "plugin") {
        const p = state.explorer.plugins.find((x) => x.id === tab.itemId);
        tab.original = p;
        tab.content = p;
      }
    } catch (e) {
      toast("加载失败", e.message, "err");
    }
  };

  // ============== 主区内容渲染 ==============
  const renderTabContent = (tab) => {
    if (!tab || !tab.content) {
      dom.tabContent.innerHTML = `<div class="panel-empty" style="padding:80px 0;">加载中…</div>`;
      return;
    }
    if (tab.type === "source") return renderSourceDetail(tab);
    if (tab.type === "channel") return renderChannelDetail(tab);
    if (tab.type === "job") return renderJobDetail(tab);
    if (tab.type === "program") return renderProgramDetail(tab);
    if (tab.type === "plugin") return renderPluginDetail(tab);
  };

  const renderSourceDetail = (tab) => {
    const s = tab.content;
    const isAdmin = state.user?.role === "admin";
    dom.tabContent.innerHTML = `
      <div class="detail">
        <div class="detail__header">
          <div>
            <div class="detail__title">${escape(s.name)}</div>
            <div class="detail__subtitle">${escape(s.id)} · ${escape(s.type)} · ${escape(s.status)}</div>
          </div>
          <div class="detail__actions">
            <button class="btn" data-act="crawl">▶ 立即抓取</button>
            ${isAdmin ? '<button class="btn" data-act="edit-json">Edit JSON</button><button class="btn btn--primary" data-act="save">Save (Ctrl+S)</button>' : ""}
            <button class="btn btn--danger" data-act="delete">删除</button>
          </div>
        </div>
        <div class="detail__body">
          <dl class="detail__grid">
            <dt>id</dt><dd>${escape(s.id)}</dd>
            <dt>name</dt><dd>${escape(s.name)}</dd>
            <dt>type</dt><dd>${escape(s.type)}</dd>
            <dt>url</dt><dd class="is-url">${escape(s.url || "—")}</dd>
            <dt>cron</dt><dd>${escape(s.cron)}</dd>
            <dt>priority</dt><dd>${s.priority}</dd>
            <dt>parser</dt><dd>${escape(s.parser)}</dd>
            <dt>status</dt><dd>${escape(s.status)}</dd>
            <dt>created_at</dt><dd>${fmtDate(s.created_at)}</dd>
            <dt>updated_at</dt><dd>${fmtDate(s.updated_at)}</dd>
          </dl>
          <div class="detail__section">
            <div class="detail__section-title">Config</div>
            <pre class="json-view" id="jsonView">${jsonHighlight(s.config)}</pre>
          </div>
          <div class="detail__section">
            <div class="detail__section-title">Headers</div>
            <pre class="json-view">${jsonHighlight(s.headers)}</pre>
          </div>
        </div>
      </div>
    `;
    bindSourceActions(tab);
    renderPanelSource(tab);
  };

  const bindSourceActions = (tab) => {
    dom.tabContent.querySelector('[data-act="crawl"]')?.addEventListener("click", () =>
      crawlSource(tab.itemId)
    );
    dom.tabContent.querySelector('[data-act="edit-json"]')?.addEventListener("click", () =>
      enableJsonEdit(tab)
    );
    dom.tabContent.querySelector('[data-act="save"]')?.addEventListener("click", () =>
      saveSource(tab)
    );
    dom.tabContent.querySelector('[data-act="delete"]')?.addEventListener("click", () =>
      deleteSource(tab.itemId)
    );
  };

  const renderChannelDetail = (tab) => {
    const c = tab.content;
    dom.tabContent.innerHTML = `
      <div class="detail">
        <div class="detail__header">
          <div>
            <div class="detail__title">${escape(c.channel_name)}</div>
            <div class="detail__subtitle">${escape(c.channel_id)} · ${escape(c.channel_country || "—")} · ${escape(c.channel_language || "—")}</div>
          </div>
        </div>
        <div class="detail__body">
          <dl class="detail__grid">
            <dt>channel_id</dt><dd>${escape(c.channel_id)}</dd>
            <dt>channel_name</dt><dd>${escape(c.channel_name)}</dd>
            <dt>country</dt><dd>${escape(c.channel_country || "—")}</dd>
            <dt>language</dt><dd>${escape(c.channel_language || "—")}</dd>
            <dt>programs</dt><dd>${c.program_count}</dd>
          </dl>
        </div>
      </div>
    `;
    renderPanelChannel(tab);
  };

  const renderJobDetail = (tab) => {
    const j = tab.content;
    dom.tabContent.innerHTML = `
      <div class="detail">
        <div class="detail__header">
          <div>
            <div class="detail__title">Job · ${escape(j.id)}</div>
            <div class="detail__subtitle">source: ${escape(j.source_id)} · trace: ${escape(j.trace_id || "—")}</div>
          </div>
          <div class="detail__actions">
            <span class="btn">${statusIcon(j.status)} ${escape(j.status)}</span>
          </div>
        </div>
        <div class="detail__body">
          <dl class="detail__grid">
            <dt>id</dt><dd>${escape(j.id)}</dd>
            <dt>source_id</dt><dd>${escape(j.source_id)}</dd>
            <dt>status</dt><dd>${escape(j.status)}</dd>
            <dt>started_at</dt><dd>${fmtDate(j.started_at)}</dd>
            <dt>finished_at</dt><dd>${fmtDate(j.finished_at)}</dd>
            <dt>items_fetched</dt><dd>${j.items_fetched}</dd>
            <dt>items_saved</dt><dd>${j.items_saved}</dd>
            <dt>trace_id</dt><dd>${escape(j.trace_id || "—")}</dd>
            ${j.error ? `<dt>error</dt><dd style="color:var(--err)">${escape(j.error)}</dd>` : ""}
          </dl>
        </div>
      </div>
    `;
    renderPanelJob(tab);
  };

  const renderProgramDetail = (tab) => {
    const p = tab.content;
    dom.tabContent.innerHTML = `
      <div class="detail">
        <div class="detail__header">
          <div>
            <div class="detail__title">${escape(p.title)}</div>
            <div class="detail__subtitle">${escape(p.channel_name || "—")} · ${fmtDate(p.start)}</div>
          </div>
        </div>
        <div class="detail__body">
          <dl class="detail__grid">
            <dt>id</dt><dd>${escape(p.id)}</dd>
            <dt>title</dt><dd>${escape(p.title)}</dd>
            <dt>channel_id</dt><dd>${escape(p.channel_id || "—")}</dd>
            <dt>channel_name</dt><dd>${escape(p.channel_name || "—")}</dd>
            <dt>start</dt><dd>${fmtDate(p.start)}</dd>
            <dt>end</dt><dd>${fmtDate(p.end)}</dd>
            <dt>timezone</dt><dd>${escape(p.timezone || "—")}</dd>
            <dt>version</dt><dd>${p.version}</dd>
            <dt>description</dt><dd>${escape(p.description || "—")}</dd>
            <dt>source_ids</dt><dd>${(p.source_ids || []).map(escape).join(", ")}</dd>
          </dl>
        </div>
      </div>
    `;
    renderPanelProgram(tab);
  };

  const renderPluginDetail = (tab) => {
    const p = tab.content;
    dom.tabContent.innerHTML = `
      <div class="detail">
        <div class="detail__header">
          <div>
            <div class="detail__title">${escape(p.name)}</div>
            <div class="detail__subtitle">${escape(p.kind)}</div>
          </div>
        </div>
        <div class="detail__body">
          <p style="color:var(--fg-1);">插件 / 解析器由注册中心管理，列表项来自 <code>/api/v1/admin/plugins</code>。</p>
        </div>
      </div>
    `;
    renderPanelPlugin(tab);
  };

  // ============== JSON 渲染 / 编辑 ==============
  const jsonHighlight = (obj) => {
    const json = JSON.stringify(obj ?? null, null, 2);
    return escape(json)
      .replace(/(&quot;[^&]+&quot;)(\s*:\s*)/g, '<span class="json-key">$1</span>$2')
      .replace(/:\s*(&quot;[^&]*&quot;)/g, ': <span class="json-string">$1</span>')
      .replace(/:\s*(-?\d+\.?\d*)/g, ': <span class="json-number">$1</span>')
      .replace(/:\s*(true|false)/g, ': <span class="json-bool">$1</span>')
      .replace(/:\s*(null)/g, ': <span class="json-null">$1</span>');
  };

  const enableJsonEdit = (tab) => {
    const pre = $("#jsonView");
    if (!pre) return;
    const ta = document.createElement("textarea");
    ta.id = "jsonView";
    ta.className = "json-view is-editing";
    ta.style.width = "100%";
    ta.style.minHeight = "300px";
    ta.style.resize = "vertical";
    ta.value = JSON.stringify(tab.content.config, null, 2);
    pre.replaceWith(ta);
    tab.dirty = true;
    renderTabs();
    ta.focus();
  };

  const saveSource = async (tab) => {
    if (state.user?.role !== "admin") {
      toast("无权限", "需要 admin 角色", "err");
      return;
    }
    try {
      const ta = document.getElementById("jsonView");
      let config = tab.content.config;
      if (ta && ta.tagName === "TEXTAREA") {
        try {
          config = JSON.parse(ta.value);
        } catch (e) {
          toast("JSON 格式错误", e.message, "err");
          return;
        }
      }
      const updated = await api(`/api/v1/sources/${tab.itemId}`, {
        method: "PUT",
        body: { config },
      });
      tab.content = updated;
      tab.original = updated;
      tab.dirty = false;
      renderTabs();
      renderTabContent(tab);
      toast("已保存", tab.itemId, "ok");
    } catch (e) {
      toast("保存失败", e.message, "err");
    }
  };

  const crawlSource = async (sourceId) => {
    try {
      dom.crawlBtn.classList.add("is-firing");
      const r = await api(`/api/v1/admin/crawl/${sourceId}`, { method: "POST" });
      toast("抓取任务已启动", `${r.job_id} · ${r.status}`, "ok");
    } catch (e) {
      toast("抓取失败", e.message, "err");
    } finally {
      setTimeout(() => dom.crawlBtn.classList.remove("is-firing"), 600);
    }
  };

  const crawlAll = async () => {
    try {
      dom.crawlBtn.classList.add("is-firing");
      const r = await api(`/api/v1/admin/crawl-all`, { method: "POST" });
      const ok = (r.results || []).filter((x) => x.ok).length;
      toast("批量抓取完成", `成功 ${ok}/${r.total}`, ok ? "ok" : "warn");
      await loadExplorer("jobs");
    } catch (e) {
      toast("批量抓取失败", e.message, "err");
    } finally {
      setTimeout(() => dom.crawlBtn.classList.remove("is-firing"), 800);
    }
  };

  const deleteSource = async (sourceId) => {
    if (!confirm(`确认删除源 ${sourceId}?`)) return;
    try {
      await api(`/api/v1/sources/${sourceId}`, { method: "DELETE" });
      toast("已删除", sourceId, "ok");
      closeTab(state.activeTabId);
      await loadExplorer("sources");
    } catch (e) {
      toast("删除失败", e.message, "err");
    }
  };

  // ============== 右侧二级面板 ==============
  const renderPanelSource = (tab) => {
    const s = tab.content;
    dom.panelTabs.innerHTML = `
      <button class="panel-tab is-active" data-p="overview">Overview</button>
      <button class="panel-tab" data-p="config">Config</button>
      <button class="panel-tab" data-p="headers">Headers</button>
      <button class="panel-tab" data-p="meta">Meta</button>
    `;
    dom.panelContent.innerHTML = `
      <div class="panel-section">
        <div class="panel-section__head">Identifier</div>
        <div class="kv-list">
          <div class="kv-row"><span class="kv-key">id</span><span class="kv-val is-mono">${escape(s.id)}</span></div>
          <div class="kv-row"><span class="kv-key">type</span><span class="kv-val">${escape(s.type)}</span></div>
          <div class="kv-row"><span class="kv-key">status</span><span class="kv-val ${s.status === "active" ? "is-ok" : ""}">${escape(s.status)}</span></div>
        </div>
      </div>
      <div class="panel-section">
        <div class="panel-section__head">URL</div>
        <div class="kv-list">
          <div class="kv-row"><span class="kv-key">endpoint</span><span class="kv-val is-mono" style="color:var(--accent)">${escape(s.url || "—")}</span></div>
          <div class="kv-row"><span class="kv-key">parser</span><span class="kv-val">${escape(s.parser)}</span></div>
        </div>
      </div>
      <div class="panel-section">
        <div class="panel-section__head">Schedule</div>
        <div class="kv-list">
          <div class="kv-row"><span class="kv-key">cron</span><span class="kv-val is-mono">${escape(s.cron)}</span></div>
          <div class="kv-row"><span class="kv-key">priority</span><span class="kv-val">${s.priority}</span></div>
        </div>
      </div>
    `;
    bindPanelTabs();
  };

  const renderPanelChannel = (tab) => {
    const c = tab.content;
    dom.panelTabs.innerHTML = `
      <button class="panel-tab is-active" data-p="overview">Overview</button>
      <button class="panel-tab" data-p="programs">Programs</button>
    `;
    dom.panelContent.innerHTML = `
      <div class="panel-section">
        <div class="panel-section__head">Channel</div>
        <div class="kv-list">
          <div class="kv-row"><span class="kv-key">id</span><span class="kv-val is-mono">${escape(c.channel_id)}</span></div>
          <div class="kv-row"><span class="kv-key">name</span><span class="kv-val">${escape(c.channel_name)}</span></div>
          <div class="kv-row"><span class="kv-key">country</span><span class="kv-val">${escape(c.channel_country || "—")}</span></div>
          <div class="kv-row"><span class="kv-key">language</span><span class="kv-val">${escape(c.channel_language || "—")}</span></div>
        </div>
      </div>
      <div class="panel-section">
        <div class="panel-section__head">Stats</div>
        <div class="kv-list">
          <div class="kv-row"><span class="kv-key">programs</span><span class="kv-val is-ok">${c.program_count}</span></div>
        </div>
      </div>
    `;
    bindPanelTabs();
  };

  const renderPanelJob = (tab) => {
    const j = tab.content;
    dom.panelTabs.innerHTML = `
      <button class="panel-tab is-active" data-p="overview">Overview</button>
      <button class="panel-tab" data-p="trace">Trace</button>
    `;
    const statusClass = j.status === "success" ? "is-ok" : j.status === "failed" ? "is-err" : "is-warn";
    dom.panelContent.innerHTML = `
      <div class="panel-section">
        <div class="panel-section__head">Status</div>
        <div class="kv-list">
          <div class="kv-row"><span class="kv-key">id</span><span class="kv-val is-mono">${escape(j.id)}</span></div>
          <div class="kv-row"><span class="kv-key">status</span><span class="kv-val ${statusClass}">${statusIcon(j.status)} ${escape(j.status)}</span></div>
          <div class="kv-row"><span class="kv-key">source</span><span class="kv-val is-mono">${escape(j.source_id)}</span></div>
        </div>
      </div>
      <div class="panel-section">
        <div class="panel-section__head">Metrics</div>
        <div class="kv-list">
          <div class="kv-row"><span class="kv-key">fetched</span><span class="kv-val is-mono">${j.items_fetched}</span></div>
          <div class="kv-row"><span class="kv-key">saved</span><span class="kv-val is-mono">${j.items_saved}</span></div>
          <div class="kv-row"><span class="kv-key">duration</span><span class="kv-val is-mono">${dur(j.started_at, j.finished_at)}</span></div>
        </div>
      </div>
    `;
    bindPanelTabs();
  };

  const renderPanelProgram = (tab) => {
    const p = tab.content;
    dom.panelTabs.innerHTML = `
      <button class="panel-tab is-active" data-p="overview">Overview</button>
      <button class="panel-tab" data-p="tags">Tags</button>
    `;
    dom.panelContent.innerHTML = `
      <div class="panel-section">
        <div class="panel-section__head">Title</div>
        <div class="kv-list">
          <div class="kv-row"><span class="kv-key">id</span><span class="kv-val is-mono">${escape(p.id)}</span></div>
          <div class="kv-row"><span class="kv-key">title</span><span class="kv-val">${escape(p.title)}</span></div>
          <div class="kv-row"><span class="kv-key">channel</span><span class="kv-val">${escape(p.channel_name || "—")}</span></div>
        </div>
      </div>
      <div class="panel-section">
        <div class="panel-section__head">Time</div>
        <div class="kv-list">
          <div class="kv-row"><span class="kv-key">start</span><span class="kv-val is-mono">${fmtDate(p.start)}</span></div>
          <div class="kv-row"><span class="kv-key">end</span><span class="kv-val is-mono">${fmtDate(p.end)}</span></div>
          <div class="kv-row"><span class="kv-key">duration</span><span class="kv-val is-mono">${dur(p.start, p.end)}</span></div>
        </div>
      </div>
    `;
    bindPanelTabs();
  };

  const renderPanelPlugin = (tab) => {
    const p = tab.content;
    dom.panelTabs.innerHTML = `<button class="panel-tab is-active" data-p="info">Info</button>`;
    dom.panelContent.innerHTML = `
      <div class="panel-section">
        <div class="panel-section__head">${escape(p.kind)}</div>
        <div class="kv-list">
          <div class="kv-row"><span class="kv-key">id</span><span class="kv-val is-mono">${escape(p.id)}</span></div>
          <div class="kv-row"><span class="kv-key">name</span><span class="kv-val">${escape(p.name)}</span></div>
        </div>
      </div>
    `;
    bindPanelTabs();
  };

  const bindPanelTabs = () => {
    $$(".panel-tab").forEach((b) => {
      b.addEventListener("click", () => {
        $$(".panel-tab").forEach((x) => x.classList.toggle("is-active", x === b));
        // 当前简单实现：只切换 is-active 样式，内容静态
      });
    });
  };

  const dur = (a, b) => {
    if (!a || !b) return "—";
    const ms = new Date(b) - new Date(a);
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  // ============== 状态栏 ==============
  const renderStatus = async () => {
    try {
      const s = await api("/api/v1/dashboard/summary");
      dom.statusDb.textContent = `◉ ${s.programs.total} programs · ${s.sources.total} sources`;
    } catch {}
    dom.statusSynced.textContent = `sync ${fmtTime(new Date().toISOString())}`;
  };

  const tickClock = () => {
    dom.statusClock.textContent = new Date().toLocaleTimeString("zh-CN", { hour12: false });
  };

  // ============== 资源操作 ==============
  const onNodeClick = async (e) => {
    const li = e.target.closest(".tree-node");
    if (!li) return;
    const type = li.dataset.type;
    const id = li.dataset.id;
    $$(".tree-node").forEach((x) => x.classList.toggle("is-active", x === li));
    const titleMap = {
      source: (id) => state.explorer.sources.find((x) => x.id === id)?.name || id,
      channel: (id) => state.explorer.channels.find((x) => x.channel_id === id)?.channel_name || id,
      job: (id) => id.slice(0, 12),
      program: (id) => state.explorer.programs.find((x) => x.id === id)?.title || id,
      plugin: (id) => state.explorer.plugins.find((x) => x.id === id)?.name || id,
    };
    const title = (titleMap[type] || ((x) => x))(id);
    await openTab(type, id, title);
  };

  const onNodeContext = (e) => {
    const li = e.target.closest(".tree-node");
    if (!li) return;
    e.preventDefault();
    state.contextNode = { type: li.dataset.type, id: li.dataset.id };
    const cm = dom.contextMenu;
    cm.hidden = false;
    cm.style.left = e.clientX + "px";
    cm.style.top = e.clientY + "px";
  };

  const onContextAction = async (e) => {
    const li = e.target.closest("[data-action]");
    if (!li) return;
    const action = li.dataset.action;
    const node = state.contextNode;
    dom.contextMenu.hidden = true;
    if (!node) return;
    if (action === "open") {
      await openTab(node.type, node.id);
    } else if (action === "crawl" && node.type === "source") {
      await crawlSource(node.id);
    } else if (action === "enable" && node.type === "source") {
      await api(`/api/v1/sources/${node.id}/enable`, { method: "POST" });
      toast("已启用", node.id, "ok");
      await loadExplorer("sources");
    } else if (action === "disable" && node.type === "source") {
      await api(`/api/v1/sources/${node.id}/disable`, { method: "POST" });
      toast("已禁用", node.id, "ok");
      await loadExplorer("sources");
    } else if (action === "delete" && node.type === "source") {
      await deleteSource(node.id);
    }
  };

  // ============== 事件绑定 ==============
  const bindUI = () => {
    // 活动栏
    $$(".activity-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const a = btn.dataset.activity;
        if (a === "crawl") return crawlAll();
        switchActivity(a);
      });
    });

    // 资源树
    dom.explorerBody.addEventListener("click", onNodeClick);
    dom.explorerBody.addEventListener("contextmenu", onNodeContext);
    dom.explorerSearch.addEventListener(
      "input",
      debounce((e) => {
        state.filter = e.target.value;
        renderExplorer();
      }, 100)
    );
    dom.explorerRefresh.addEventListener("click", () => loadExplorer(state.activity));

    // Tab bar（事件委托）
    dom.tabBar.addEventListener("click", (e) => {
      const close = e.target.closest("[data-close]");
      if (close) {
        e.stopPropagation();
        closeTab(close.dataset.close);
        return;
      }
      const tab = e.target.closest(".tab");
      if (tab) switchTab(tab.dataset.tab);
    });

    // 顶栏账号
    dom.accountBtn.addEventListener("click", () => {
      dom.accountDropdown.hidden = !dom.accountDropdown.hidden;
    });
    document.addEventListener("click", (e) => {
      if (!dom.accountMenu.contains(e.target)) dom.accountDropdown.hidden = true;
    });
    dom.accountAction.addEventListener("click", () => {
      if (state.token) doLogout();
      else showLogin();
    });

    // 命令面板（占位）
    dom.cmdPalette.addEventListener("click", () => {
      toast("命令面板", "Ctrl+K 占位，暂未实现", "info", 2000);
    });

    // 登录表单
    dom.loginForm.addEventListener("submit", (e) => {
      e.preventDefault();
      doLogin(dom.loginUser.value, dom.loginPass.value);
    });

    // 全局快捷键
    document.addEventListener("keydown", (e) => {
      // Ctrl+S / Cmd+S 保存
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        const tab = state.tabs.find((t) => t.id === state.activeTabId);
        if (tab && tab.type === "source" && tab.dirty) saveSource(tab);
      }
      // / 聚焦搜索
      if (e.key === "/" && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
        e.preventDefault();
        dom.explorerSearch.focus();
      }
      // Esc 关闭登录面板 / 右键菜单
      if (e.key === "Escape") {
        if (!dom.loginOverlay.hidden) hideLogin();
        dom.contextMenu.hidden = true;
      }
    });

    // 右键菜单
    dom.contextMenu.addEventListener("click", onContextAction);
    document.addEventListener("click", (e) => {
      if (!dom.contextMenu.contains(e.target)) dom.contextMenu.hidden = true;
    });
  };

  // ============== 启动 ==============
  const refreshAll = async () => {
    await loadExplorer(state.activity);
    await renderStatus();
  };

  const start = async () => {
    updateAccount();
    bindUI();
    tickClock();
    setInterval(tickClock, 1000);
    setInterval(refreshAll, 30000);
    if (!state.token) {
      showLogin();
    } else {
      await refreshAll();
    }
  };

  document.addEventListener("DOMContentLoaded", start);
})();
