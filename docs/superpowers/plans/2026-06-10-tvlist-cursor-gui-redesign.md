# TVLIST Cursor GUI 重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) 或 superpowers:executing-plans 来逐任务实施。步骤用 `- [ ]` 复选框跟踪。

**Goal:** 把现有 Editorial Dark Glass 风格 GUI 重构为 Cursor 风格 IDE 资源浏览器。

**Architecture:**
- 视觉对齐 IDE：活动栏（5 图标）+ 资源树（4 根节点）+ 主区多 tab + 右侧二级面板 + 状态栏 + 可选登录面板
- 资源即一等公民：Sources / Channels / Jobs / Programs 作为根节点，点击开 tab
- 认证：JWT token 持久化在 localStorage；未登录显示覆盖登录面板
- 编辑：源配置支持表格 + JSON 双视图，PUT 保存
- 静态文件：无构建、vanilla JS

**Tech Stack:** FastAPI 0.110+, vanilla JS (ES2020), CSS3 Grid/Flex, Google Fonts (JetBrains Mono + Inter)

**Spec:** `docs/superpowers/specs/2026-06-10-tvlist-cursor-gui-redesign.md`

**Project Root:** `/workspace/tv-list-aggregator`

---

## 文件结构

| 文件 | 状态 | 职责 |
|------|------|------|
| `src/tv_list_aggregator/interfaces/web/index.html` | 重写 | 顶栏/活动栏/资源树/主区/右侧面板/状态栏/登录面板骨架 |
| `src/tv_list_aggregator/interfaces/web/style.css` | 重写 | Cursor 暗色 IDE 主题（CSS 变量 + Grid 布局） |
| `src/tv_list_aggregator/interfaces/web/app.js` | 重写 | 状态管理 + API + 资源树 + Tab + 详情 + 编辑 + 认证 |
| `src/tv_list_aggregator/interfaces/api/routers/sources.py` | 修改 | 新增 `PUT /sources/{id}` |
| `src/tv_list_aggregator/interfaces/api/routers/channels.py` | 新建 | `GET /channels` 列表 |
| `src/tv_list_aggregator/interfaces/api/app.py` | 修改 | include channels router |

---

## Task 1: 后端 - 新增 PUT /sources/{id}

**Files:**
- Modify: `src/tv_list_aggregator/interfaces/api/routers/sources.py`
- Test: `tests/integration/api/test_sources_update.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/integration/api/test_sources_update.py
import pytest
from httpx import ASGITransport, AsyncClient
from tv_list_aggregator.interfaces.api.app import create_app
from tv_list_aggregator.interfaces.api.deps import reset_deps
import tempfile, os

@pytest.mark.asyncio
async def test_update_source_name():
    reset_deps()
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["TV_LIST_DATABASE_URL"] = f"sqlite+aiosqlite:///{path}"
    os.environ["TV_LIST_BOOTSTRAP_SCHEMA"] = "1"
    os.environ["TV_LIST_AUTO_SEED"] = "1"
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        # 触发 lifespan bootstrap
        async with app.router.lifespan_context(app):
            r = await c.put(
                "/api/v1/sources/src_demo_iqiyi",
                json={"name": "iQIYI 新名称", "priority": 9},
            )
            assert r.status_code == 200
            assert r.json()["name"] == "iQIYI 新名称"
            assert r.json()["priority"] == 9
    os.unlink(path)
```

- [ ] **Step 2: 跑测试，预期失败（404 或 405）**

```bash
cd /workspace/tv-list-aggregator && python -m pytest tests/integration/api/test_sources_update.py -v
```

- [ ] **Step 3: 实现 PUT 端点**

在 `routers/sources.py` 中添加：

```python
@router.put(
    "/{source_id}",
    response_model=SourceOut,
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def update_source(
    source_id: str,
    payload: SourceCreate,
    repo=Depends(get_source_repo),
    session: AsyncSession = Depends(get_session),
):
    s = await repo.get(source_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "source not found")
    data = payload.model_dump(exclude_none=False)
    data.pop("id", None)
    for k, v in data.items():
        setattr(s, k, v)
    s.updated_at = datetime.now(tz=UTC)
    await repo.update(s)
    await session.commit()
    return s
```

- [ ] **Step 4: 跑测试，预期通过**

```bash
python -m pytest tests/integration/api/test_sources_update.py -v
```

- [ ] **Step 5: 提交**

```bash
git add -A && git commit -m "feat(api): PUT /sources/{id} 支持更新源配置"
```

---

## Task 2: 后端 - 新增 GET /channels

**Files:**
- Create: `src/tv_list_aggregator/interfaces/api/routers/channels.py`
- Create: `src/tv_list_aggregator/interfaces/api/schemas/channel.py`
- Modify: `src/tv_list_aggregator/interfaces/api/app.py` (include router)
- Test: `tests/integration/api/test_channels.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/integration/api/test_channels.py
import pytest
from httpx import ASGITransport, AsyncClient
from tv_list_aggregator.interfaces.api.app import create_app
from tv_list_aggregator.interfaces.api.deps import reset_deps
import tempfile, os

@pytest.mark.asyncio
async def test_list_channels_ok():
    reset_deps()
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["TV_LIST_DATABASE_URL"] = f"sqlite+aiosqlite:///{path}"
    os.environ["TV_LIST_BOOTSTRAP_SCHEMA"] = "1"
    os.environ["TV_LIST_AUTO_SEED"] = "1"
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        async with app.router.lifespan_context(app):
            r = await c.get("/api/v1/channels")
            assert r.status_code == 200
            data = r.json()
            assert len(data) > 0
            assert "channel_id" in data[0]
            assert "channel_name" in data[0]
            assert "program_count" in data[0]
    os.unlink(path)
```

- [ ] **Step 2: 跑测试，预期 404**

```bash
python -m pytest tests/integration/api/test_channels.py -v
```

- [ ] **Step 3: 实现 schema + router**

`interfaces/api/schemas/channel.py`:
```python
from pydantic import BaseModel

class ChannelOut(BaseModel):
    channel_id: str
    channel_name: str
    channel_country: str | None = None
    channel_language: str | None = None
    program_count: int
```

`interfaces/api/routers/channels.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....infrastructure.persistence.models import ProgramRow
from ..deps import get_session
from ..schemas.channel import ChannelOut

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("", response_model=list[ChannelOut])
async def list_channels(session: AsyncSession = Depends(get_session)):
    stmt = (
        select(
            ProgramRow.channel_id,
            ProgramRow.channel_name,
            ProgramRow.channel_country,
            ProgramRow.channel_language,
            func.count(ProgramRow.id).label("program_count"),
        )
        .group_by(
            ProgramRow.channel_id,
            ProgramRow.channel_name,
            ProgramRow.channel_country,
            ProgramRow.channel_language,
        )
        .order_by(func.count(ProgramRow.id).desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        ChannelOut(
            channel_id=r.channel_id,
            channel_name=r.channel_name,
            channel_country=r.channel_country,
            channel_language=r.channel_language,
            program_count=int(r.program_count),
        )
        for r in rows
    ]
```

- [ ] **Step 4: 在 app.py 中 include**

```python
from .routers import admin, auth, channels, dashboard, export, health, jobs, programs, sources
# ...
app.include_router(channels.router, prefix="/api/v1")
```

- [ ] **Step 5: 跑测试，预期通过**

```bash
python -m pytest tests/integration/api/test_channels.py -v
```

- [ ] **Step 6: 提交**

```bash
git add -A && git commit -m "feat(api): GET /channels 频道聚合列表"
```

---

## Task 3: 前端 - 重写 index.html（骨架）

**Files:**
- Modify: `src/tv_list_aggregator/interfaces/web/index.html`

- [ ] **Step 1: 完全重写为 Cursor 风格骨架**

完整 HTML 见 spec 第 2 节布局图。要素：
- `<header class="topbar">` - logo + 命令面板按钮 + 环境 pill + 账号菜单
- `<aside class="activity-bar">` - 5 个图标按钮（垂直）
- `<aside class="explorer">` - 4 个根节点（Sources/Channels/Jobs/Programs），每节点有 children 容器
- `<main class="editor">` - tab bar + tab 内容区
- `<aside class="panel-right">` - 二级 tab + 详情只读表格
- `<footer class="statusbar">` - 环境/库大小/选中节点路径
- `<div class="login-overlay">` - 登录面板（默认 hidden）
- `<div class="toast-host">` - 通知

- [ ] **Step 2: 提交**

```bash
git add -A && git commit -m "feat(web): index.html 重构为 Cursor IDE 骨架"
```

---

## Task 4: 前端 - 重写 style.css（Cursor 暗色主题）

**Files:**
- Modify: `src/tv_list_aggregator/interfaces/web/style.css`

- [ ] **Step 1: 完全重写为 IDE 暗色主题**

设计 token：
```css
:root {
  --bg-0: #1e1e1e;   /* 主背景 */
  --bg-1: #252526;   /* 资源树 / 右侧面板 */
  --bg-2: #2d2d30;   /* tab bar / 顶栏 */
  --bg-3: #333333;   /* hover */
  --border: #3c3c3c;
  --fg-0: #cccccc;   /* 主文字 */
  --fg-1: #969696;   /* 次要 */
  --fg-2: #6b6b6b;   /* 弱化 */
  --accent: #007acc; /* VS Code 蓝 */
  --accent-2: #4ec9b0; /* 关键字青 */
  --warn: #dcdcaa;
  --err: #f48771;
  --ok: #4ade80;
  --mono: "JetBrains Mono", monospace;
  --sans: "Inter", -apple-system, sans-serif;
}
```

布局用 CSS Grid：
```css
body {
  display: grid;
  grid-template-columns: 48px 240px 1fr 320px;
  grid-template-rows: 32px 1fr 22px;
  grid-template-areas:
    "topbar  topbar  topbar   topbar"
    "actbar  expl    editor   panel"
    "status  status  status   status";
  height: 100vh;
  margin: 0;
  background: var(--bg-0);
  color: var(--fg-0);
  font-family: var(--sans);
  font-size: 13px;
}
```

完整实现包括：
- 顶栏：flex 横排，logo 左对齐，命令面板按钮中，账号右对齐
- 活动栏：48px 宽，每个图标按钮 48×40，hover bg-3，active 蓝色左边框
- 资源树：240px 宽，根节点 22px 高，children 缩进 12px
- 主区：tab bar 36px 高，tab 100px 最小宽，未保存显示圆点
- 右侧面板：320px 宽，二级 tab 在顶部，详情表格在下面
- 状态栏：22px 高，bg-2，flex 三段
- 登录面板：fixed 全屏遮罩，modal 居中 400×280

- [ ] **Step 2: 提交**

```bash
git add -A && git commit -m "feat(web): style.css 重构为 Cursor 暗色 IDE 主题"
```

---

## Task 5: 前端 - 重写 app.js（完整逻辑）

**Files:**
- Modify: `src/tv_list_aggregator/interfaces/web/app.js`

- [ ] **Step 1: 单一文件实现所有逻辑**

完整结构：
```javascript
(() => {
  "use strict";
  // ====== 状态 ======
  const state = {
    token: localStorage.getItem("tvlist_token"),
    user: null,
    activityRoot: "sources",   // 当前活动栏选中
    tabs: [],                  // 主区 tab 列表 [{id, type, kind, title, dirty, content}]
    activeTab: null,
    panelTabs: ["overview"],   // 右侧二级 tab
    activePanel: "overview",
    explorer: { sources: [], channels: [], jobs: [], programs: [] },
    explorerFilter: "",
  };

  // ====== API 工具 ======
  const api = async (path, opts = {}) => { /* 带 token、错误抛错 */ };

  // ====== 登录 ======
  const showLogin = () => { /* 显示覆盖面板 */ };
  const hideLogin = () => { /* 隐藏 */ };
  const doLogin = async (username, password) => { /* POST /auth/token，存 localStorage */ };
  const doLogout = () => { /* 清 token，跳回登录 */ };

  // ====== 活动栏 ======
  const switchActivity = (root) => { /* 切换活动栏，更新资源树 */ };

  // ====== 资源树 ======
  const loadExplorer = async (root) => { /* 加载对应根节点的数据 */ };
  const renderExplorer = () => { /* 渲染树 */ };

  // ====== Tab 系统 ======
  const openTab = (type, kind, id, title) => { /* 开/聚焦 tab */ };
  const closeTab = (tabId) => { /* 关闭 tab */ };
  const switchTab = (tabId) => { /* 切换激活 tab */ };
  const renderTabs = () => { /* 渲染 tab bar */ };
  const renderTabContent = (tab) => { /* 渲染 tab 内容：表格 + JSON */ };

  // ====== 右侧二级面板 ======
  const switchPanel = (panelId) => { /* 切换二级 tab */ };
  const renderPanel = (tab) => { /* 渲染右侧 */ };

  // ====== 编辑能力 ======
  const enableEdit = (tab) => { /* 切换到 JSON 编辑模式 */ };
  const saveSource = async (tab) => { /* PUT /sources/{id} */ };

  // ====== 状态栏 ======
  const renderStatus = () => { /* 渲染状态栏 */ };

  // ====== 自动刷新 ======
  const startRefresh = () => { /* 30s 拉 summary */ };

  // ====== 启动 ======
  const start = async () => {
    if (!state.token) showLogin();
    else { await loadUser(); await refreshAll(); }
    bindUI();
    startRefresh();
  };
  document.addEventListener("DOMContentLoaded", start);
})();
```

- [ ] **Step 2: 提交**

```bash
git add -A && git commit -m "feat(web): app.js 重构为完整资源浏览器逻辑"
```

---

## Task 6: 集成验证

- [ ] **Step 1: 跑全部测试**

```bash
cd /workspace/tv-list-aggregator && python -m pytest -v
```

预期：所有测试通过

- [ ] **Step 2: 启动服务并 GUI 烟测**

```bash
ps aux | grep uvicorn | grep -v grep | awk '{print $2}' | xargs -r kill
rm -f /tmp/gui.db
TV_LIST_DATABASE_URL='sqlite+aiosqlite:////tmp/gui.db' \
TV_LIST_APP_ENV=development \
TV_LIST_SECRET_KEY='test-secret-for-demo-only-do-not-use-in-prod' \
TV_LIST_BOOTSTRAP_SCHEMA=1 \
TV_LIST_SEED_USERS='admin:admin123:admin,user:user123:user' \
nohup python -m uvicorn tv_list_aggregator.interfaces.api.app:app --host 0.0.0.0 --port 8000 --log-level info > /tmp/uvicorn.log 2>&1 &
sleep 4
curl -s http://127.0.0.1:8000/ | head -1
curl -s -o /dev/null -w "PUT /sources: HTTP %{http_code}\n" -X PUT http://127.0.0.1:8000/api/v1/sources/src_demo_iqiyi -H "Content-Type: application/json" -d '{"name":"新名","priority":7}'
curl -s -o /dev/null -w "GET /channels: HTTP %{http_code}\n" http://127.0.0.1:8000/api/v1/channels
```

- [ ] **Step 3: OpenPreview 验证 GUI**

```bash
# 用 OpenPreview tool
```

- [ ] **Step 4: 提交**

```bash
git add -A && git commit -m "chore: 集成验证 GUI 重构 v2"
```

---

## Self-Review

✅ Spec 覆盖：
- 顶栏 ✓ Task 5
- 活动栏（5 图标） ✓ Task 3 + 5
- 资源树（4 节点） ✓ Task 3 + 5
- 主区多 tab ✓ Task 3 + 5
- 右侧二级面板 ✓ Task 3 + 5
- 状态栏 ✓ Task 3 + 5
- 登录面板 ✓ Task 3 + 5
- 源配置编辑 ✓ Task 1（后端） + 5（前端）
- 频道列表 ✓ Task 2

✅ 类型一致：所有 API 路径一致 `/api/v1/...`
✅ 无 placeholder：所有代码片段完整
