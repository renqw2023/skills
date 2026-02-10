中文 | [**English**](README.md)

# Task Sync

**滴答清单** 与 **Google Tasks** 双向同步工具，支持智能列表。

基于 [OpenClaw](https://openclaw.ai/) 技能构建 — 可通过 cron 自动运行或手动执行。

## 功能特性

- **双向列表同步** — Google 任务列表与滴答清单项目按名称自动匹配或创建
- **双向任务同步** — 标题、完成状态、备注/内容
- **优先级映射** — 滴答清单优先级显示为 Google 任务标题前缀（`[★]` 高优先级、`[!]` 中优先级）
- **智能列表**（单向，滴答清单 → Google）：
  - **Today** — 已过期 + 今日任务
  - **Next 7 Days** — 未来一周
  - **All** — 所有活跃任务（含日期）
- **日期策略** — 防止 Google Calendar 出现重复任务（见下文）
- **幂等运行** — 可重复执行，不会产生重复数据

## 日期策略

Google Tasks 中带日期的任务会自动显示在 Google Calendar 中。为防止跨列表重复，日期的处理策略如下：

| 列表类型 | Google 中是否含日期 | 原因 |
|----------|:-:|------|
| 常规列表 | 否 | 日期转发到滴答清单后从 Google 清除 |
| "All" 智能列表 | 是 | Calendar 唯一数据源 |
| "Today" / "Next 7 Days" | 否 | 仅作为过滤视图 |

## 架构

```
sync.py                        主同步脚本
utils/
  google_api.py                Google Tasks API 封装（分页、Token 自动刷新）
  ticktick_api.py              滴答清单 Open API 封装
scripts/
  setup_google_tasks.py        Google OAuth 授权设置
  setup_ticktick.py            滴答清单 OAuth 授权设置
config.json                    配置文件（Token 路径、数据文件路径）
sync_db.json                   任务映射数据库（自动生成）
sync_log.json                  同步统计日志（自动生成）
e2e_test.py                    端到端测试（15 个测试用例）
```

### 同步流程

```
1. 列表同步（双向）
   Google Lists <──────────> 滴答清单 Projects
   - 按名称匹配（不区分大小写）
   - "My Tasks" <-> "收集箱" (Inbox)（特殊映射）
   - 未匹配的列表自动创建对应项

2. 任务同步（双向，按列表对同步）
   Google Tasks <──────────> 滴答清单 Tasks
   - 新任务双向同步
   - 完成状态双向传播
   - 日期：Google → 滴答清单（转发后清除）
   - 优先级：滴答清单 → Google（标题前缀）
   - 备注/内容在创建时同步

3. 智能列表（单向：滴答清单 → Google）
   滴答清单 ──────────────> Google "Today" / "Next 7 Days" / "All"
   - 不再匹配的任务自动移除
```

## 安装配置

### 前置要求

- Python 3.10+
- 已启用 Tasks API 的 Google Cloud 项目
- 滴答清单开发者应用（从 [developer.ticktick.com](https://developer.ticktick.com/) 创建）

### 1. 安装依赖

```bash
pip install google-auth google-auth-oauthlib google-api-python-client requests
```

### 2. 配置 Google Tasks

```bash
python scripts/setup_google_tasks.py
```

按照 OAuth 流程授权，Token 会保存到 `config/` 或你配置的路径。

### 3. 配置滴答清单

```bash
python scripts/setup_ticktick.py
```

按照 OAuth 流程操作，需要你的滴答清单应用的 Client ID 和 Client Secret。

### 4. 编辑 config.json

```json
{
  "google_token": "/path/to/google/token.json",
  "ticktick_token": "/path/to/ticktick/token.json",
  "sync_db": "/path/to/sync_db.json",
  "sync_log": "/path/to/sync_log.json",
  "ticktick_api_base": "https://api.ticktick.com/open/v1"
}
```

### 5. 运行

```bash
python sync.py
```

## 自动化

设置 cron 定时同步：

```bash
# 每 10 分钟同步一次
*/10 * * * * /path/to/python /path/to/sync.py >> /path/to/sync.log 2>&1
```

或使用 OpenClaw 内置的 cron 系统进行托管调度。

## 测试

项目包含完整的端到端测试套件，基于真实 API 测试：

```bash
python e2e_test.py
```

### 测试覆盖（15 个测试）

| # | 测试内容 | 方向 |
|---|---------|------|
| 1 | 新任务同步 | Google → 滴答清单 |
| 2 | 新任务同步 | 滴答清单 → Google |
| 3 | 完成状态同步 | Google → 滴答清单 |
| 4 | 完成状态同步 | 滴答清单 → Google |
| 5 | 日期转发并清除 | Google → 滴答清单 |
| 6 | 日期仅出现在 "All" 列表 | 滴答清单 → Google |
| 7 | "Today" 智能列表填充 | 滴答清单 → Google |
| 8 | "Next 7 Days" 智能列表填充 | 滴答清单 → Google |
| 9 | 高优先级 `[★]` 前缀 | 滴答清单 → Google |
| 10 | 智能列表名称不泄漏到滴答清单 | 防护测试 |
| 11 | 中优先级 `[!]` 前缀 | 滴答清单 → Google |
| 12 | 备注/内容同步 | Google → 滴答清单 |
| 13 | 幂等性（无重复） | 双向 |
| 14 | 新列表 → 项目创建 | Google → 滴答清单 |
| 15 | 过期智能列表任务移除 | 清理 |

## API 参考

- [Google Tasks REST API](https://developers.google.com/workspace/tasks/reference/rest)
- [滴答清单 Open API](https://developer.ticktick.com/)

## 许可证

MIT
