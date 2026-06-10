# TVLIST GUI 重构设计：Cursor 风格资源浏览器

**日期**：2026-06-10
**版本**：v2.0（重做 GUI）
**作者**：brainstorming 阶段产出

## 1. 背景与目标

当前 GUI 走的是"Codex 风格"暗色卡片+大字号+编辑感版式的设计，用户反馈"不是我想要的"。本文档重新设计为 **Cursor 风格 IDE 资源浏览器**，让用户像浏览代码仓库一样浏览数据源、频道、节目和任务。

### 目标

- 视觉语言对齐 IDE：活动栏、资源树、tab、终端、状态栏
- 资源即一等公民：4 种资源类型（Sources / Channels / Jobs / Programs）作为根节点
- 可写：源配置支持表格 + JSON 双视图编辑
- 全局 token 认证，左下角账号菜单

## 2. 布局与组件

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ▦  TVLIST   ⌘K  搜索命令...            [env: dev]   ◉ alice  ▾              │ ← 顶栏
├────┬──────────────┬───────────────────────────────────────────┬──────────────┤
│ ⓘ  │ ▾ Sources    │ [Sources · 3]   [Channels · 12]   [Jobs ·] │ ▾ OVERVIEW  │
│    │   ▸ iQIYI    │   [Programs · 668]                          │             │
│ ⊞  │   ▸ CCTV     │ ─────────────────────────────────────────── │  id         │
│    │   ▸ IPTV     │                                            │  src_demo.. │
│ ⏱  │ ▾ Channels   │  iQIYI 热播剧场            active  ↻ edit │             │
│    │   ▸ CCTV-1   │  ───────────────────────────────────────── │  name       │
│ ▤  │   ▸ BBC One  │  type:       http_json                     │  iQIYI 热播 │
│    │   ...        │  url:        https://demo...               │             │
│ ⚙  │ ▾ Jobs       │  cron:       */15 * * * *                  │  type       │
│    │   ▸ Job #123 │  parser:     auto                          │  http_json  │
│ 👤 │ ▾ Programs   │  status:     active                        │             │
│    │   ...        │                                            │  config     │
├────┴──────────────┤  ── 二级 tab ────────────────────────────  │  {}         │
│ status: dev · 3  │  [Overview] [Config JSON] [Schedule] [Jobs]│             │
│ ⓘ ready         │                                            │  [Edit JSON]│
└──────────────────┴────────────────────────────────────────────┴──────────────┘
   ↑活动栏   ↑资源树      ↑主区多 tab                ↑右侧二级 tab + 详情
```

### 组件清单

1. **顶栏 Topbar**
   - 左：logo + 品牌名
   - 中：命令面板触发按钮（`⌘K` / `Ctrl+K`）
   - 右：环境标识 pill + 账号菜单（点击下拉：当前用户 / 退出 / 重新登录）

2. **活动栏 ActivityBar**（左侧 6 个图标，垂直）
   - `ⓘ` Sources（默认选中）
   - `⊞` Channels
   - `▤` Jobs
   - `▦` Programs
   - `⚙` Plugins（管理员视角）
   - `👤` Account

3. **资源树 Explorer**（活动栏右侧面板）
   - 每个根节点是一个资源类型
   - 叶子是具体资源（点击 → 在主区开 tab）
   - 右键菜单：删除/启用/禁用/立即抓取/查看详情
   - 顶部小搜索框（资源内过滤）

4. **主区 Tab 区**
   - 顶部：tab bar（可拖拽重排，关闭按钮）
   - 内容：根据 tab 类型显示（默认渲染"欢迎页"）
   - tab 关闭：×按钮；未保存：显示圆点
   - 标签：`[type · count]`，例：`[Sources · 3]`

5. **右侧二级面板**
   - 选中主区 tab 后，右侧显示该资源的二级视图
   - 二级 tab：`Overview / Config JSON / Schedule / Jobs`（Sources） 或 `EPG / Programs / Raw`（Channels） 或 `Overview / Logs / Raw`（Jobs）
   - 右侧顶部：面包屑显示选中节点路径
   - 右侧底部：详情只读表格（键值对）

6. **状态栏 StatusBar**（底部 24px）
   - 左：环境 + 库大小（节目总数）
   - 中：当前选中节点路径
   - 右：网络状态 / 同步时间

## 3. 资源模型

| 资源 | 树结构 | 节点字段 | 主 tab 视图 | 二级 tab |
|------|-------|---------|------------|----------|
| **Sources** | 源列表 | id, name, type, status | 详情表格 + JSON | Overview / Config JSON / Schedule / Jobs |
| **Channels** | 频道列表 | id, name, category, programs_count | 详情表格 + JSON | EPG / Programs / Raw |
| **Jobs** | 任务列表（按 status 分组） | id, source_id, status, started_at | 详情 + 日志 | Overview / Logs / Raw Output |
| **Programs** | 节目列表（按日期分组） | id, title, channel_name, start | 详情 | Details / Source IDs / Tags |

## 4. 编辑能力

- **Sources 配置**支持双视图：
  - **表格视图**：键值对表单
  - **JSON 视图**：textarea 实时编辑
- 保存：右上角 `⌘S` 或 `Save` 按钮 → 调 `PUT /api/v1/sources/{id}`（需后端新增）
- 失败提示：底部 toast（错误信息 + request_id）

## 5. 认证

- 启动时若 `localStorage.tvlist_token` 为空 → 显示登录面板（覆盖在主界面之上）
- 登录面板：用户名 + 密码 → `POST /api/v1/auth/token` → 存 token → 关闭面板
- 顶栏右侧：账号菜单显示当前用户（解码 JWT 的 sub 字段）
- 退出：清 token + 跳回登录面板
- API 调用统一带 `Authorization: Bearer <token>`（前端 `api()` 工具已实现）

## 6. 技术栈

- **前端**：vanilla JS + CSS（无框架，无构建步骤，便于直接挂载）
- **后端**：FastAPI（已存在）
- **数据流**：fetch API → JSON；无状态
- **路由**：URL 同步（`?path=sources/src_demo_iqiyi`）支持深链接与刷新
- **持久化**：localStorage 存 token + 当前 tab/path

## 7. 文件结构

```
src/tv_list_aggregator/interfaces/web/
├── index.html           # 单页布局骨架
├── style.css            # IDE 风格主题
└── app.js               # 资源树、tab、状态管理
```

静态资源已通过 FastAPI 挂在 `/static/`。无需新增后端端点（除 `PUT /api/v1/sources/{id}`）。

## 8. 验收标准

- [ ] 4 种资源类型在活动栏全部可访问
- [ ] 资源树点击节点在主区开 tab，可关闭可重排
- [ ] 选中 tab 时右侧二级 tab 自动切换
- [ ] Sources 节点支持表格/JSON 双视图编辑并能保存
- [ ] 未登录时显示登录面板，登录后关闭
- [ ] 顶栏账号菜单显示当前用户、退出按钮
- [ ] 状态栏显示环境与库大小
- [ ] 资源搜索可在树内即时过滤
- [ ] 桌面端 1280×800 完整呈现不溢出
- [ ] 30s 自动刷新 + 手动刷新按钮 + crawl 按钮

## 9. 范围之外（YAGNI）

- 多主题切换（仅暗色）
- 拖拽 tab 重排（先做静态 tab bar）
- 命令面板 ⌘K 高级功能（先做按钮占位）
- 终端面板（先不做）
- 协作编辑（单人使用）
- i18n（先中文）

## 10. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 编辑源后端端点缺失 | 保存失败 | 方案：临时只读，标记"编辑功能开发中" |
| 桌面布局在小屏不友好 | 体验差 | 至少 1280px 起步，移动端后续 |
| 大量资源（>1000 节点）性能 | 树渲染卡顿 | 资源树虚拟化（先做 lazy expand） |
