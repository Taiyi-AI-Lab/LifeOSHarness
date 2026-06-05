# LifeOS Platform API

LifeOS 将「Agent 世界」（人设、行为轨迹、世界规则、运行时 persona/emotion/memory/world 状态）托管在服务端，各 Agent 运行时通过 Connector 拉取 context 并回写 session 事件。

## 架构

- **Server**：FastAPI + SQLAlchemy 核心存储（默认 SQLite，可选 PostgreSQL）+ Redis（context 短缓存，可选）
- **Client**：`lifeos` CLI / Python SDK
- **陈远**：示例 preset `POST /packs/presets/chenyuan`

## 认证

请求 Header：

```http
X-API-Key: <LIFEOS_API_KEY>
```

## 核心流程

1. `POST /packs/presets/chenyuan` 或 `POST /packs` 创建 Pack
2. `POST /worlds` 创建 WorldInstance
3. `POST /runtime/session/start` — pi 会话级绑定（首次）
4. `POST /runtime/turn/begin` — 单轮开始（情绪 `chat_started`）
5. `POST /runtime/context` — 获取注入块
6. `POST /runtime/turn/finish` — 单轮结束（情绪 `chat_ended`）
7. `POST /runtime/session/end` — pi 会话结束

## Claude Code 联动

安装、验证与卸载的完整步骤见：

**[`docs/claude-code-connector.md`](../claude-code-connector.md)**

快速安装：

```bash
uv run lifeos connector install claude-code
```

Hook 写入 `~/.claude/settings.json`；脚本 `~/.lifeos/hooks/lifeos_hook.py`。`UserPromptSubmit` 时输出 `additionalContext`（完整 陈远/system 块）。

## Codex 联动

安装、验证与卸载的完整步骤见：

**[`docs/codex-connector.md`](../codex-connector.md)**

快速安装：

```bash
uv run lifeos connector install codex
```

`~/.codex/hooks.json` + `config.toml` 中 `hooks = true`；脚本与 Claude Code 共用 `~/.lifeos/hooks/lifeos_hook.py`，`connector_id` 为 `codex`。

## Hermes 联动（Python Plugin）

安装、在 Hermes 中 **enable**、验证与卸载的完整步骤见：

**[`docs/hermes-connector.md`](../hermes-connector.md)**

快速安装：

```bash
uv run lifeos connector install hermes
hermes plugins enable lifeos   # 必做：Hermes 插件默认不加载
```

Hook 映射：`on_session_start` / `pre_llm_call` / `post_llm_call` / `on_session_end` → 对应 `/runtime/session/*` 与 `/runtime/turn/*`、`/runtime/context`。`pre_llm_call` 将 LifeOS `system` 块注入 **user message**。

## OpenClaw 联动

安装、验证与卸载的完整步骤见：

**[`docs/openclaw-connector.md`](../openclaw-connector.md)**

快速安装：

```bash
uv run lifeos connector install openclaw
openclaw plugins enable lifeos
openclaw gateway restart
```

`before_prompt_build` 合并 **system prompt**；`connector_id` 为 `openclaw`。

## pi CLI 联动

安装、验证与卸载的完整步骤见：

**[`docs/pi-connector.md`](../pi-connector.md)**

快速安装：

```bash
uv run lifeos connector install pi
uv run lifeos login && uv run lifeos world-create --pack chenyuan
pi    # 会话内可用 /lifeos 检查连接
```

Extension 安装到 `~/.pi/agent/extensions/lifeos.ts`，通过 `before_agent_start` 合并 **system prompt**。

## Context 请求示例

```json
{
  "world_id": "uuid",
  "user_message": "今天有点累",
  "connector_id": "claude-code",
  "session_id": "optional-session-id",
  "interaction_intent": "auto"
}
```

`interaction_intent` 可选：

- `auto`（默认）：服务端按 `LIFEOS_INTENT_CLASSIFIER` 分类。
- `chitchat`：强制注入 LifeOS context。
- `task`：强制跳过 LifeOS context。

响应新增意图门控字段：

```json
{
  "resolved_intent": "chitchat",
  "injected": true,
  "intent_classifier": "rules",
  "intent_reason": "命中闲聊/陪伴信号。"
}
```

当 `resolved_intent=task` 时，`system=""`、`order=[]`、`blocks=[]`、`injected=false`。默认规则分类优先识别代码、测试、文件、搜索、总结、翻译、生成产物、工具操作等任务信号；未知消息也按 task 处理，避免误注入。

配置 `LIFEOS_INTENT_CLASSIFIER=llm` 后，服务端使用 DeepSeek 意图分类，模型由 `DEEPSEEK_INTENT_MODEL` 指定；无 API key、超时、低置信度或非法 JSON 时自动回退规则分类。

响应 `system` 字段由 [`PromptComposer`](../../lifeostomanyagent/server/engine/prompt_composer.py) 按 `connector_id` 组装，块顺序如下：

| 块 ID | 说明 | 外部 Connector | pi |
|-------|------|----------------|-----|
| `platform_guardrails` | 平台保密规则 | 是 | 是 |
| `agent_identity` | Pack 身份（结构化） | 是 | 是 |
| `behavior_profile` | 说话风格 / 禁止表达 | 是 | 是 |
| `behavior_trajectory` | 行为轨迹 / 反应模式 | 是 | 是 |
| `world_rules` | 时区 / 地点 / 世界事实 | 是 | 是 |
| `persona_state` | 运行时 `<agent_persona>` | 是 | 是 |
| `emotion_state` | 运行时 `<agent_emotion>` | 是 | 是 |
| `user_memory` | 运行时 `<user_memory_update>` | 是 | 是 |
| `world_facts` | 运行时 World Facts | 是 | 是 |
| `connector_overlay` | pi 工具 playbook | **否** | 是（压缩适配 28KB 预算） |
| `user_message` | 当前用户输入 | 是 | 是 |

外部 Connector（`hermes` / `claude-code` / `codex` / `openclaw`）默认 **不含** pi/陈远 工具说明（OOXML、novel_write、Skills 列表等）；这些在 [`server/overlays/pi_tools.md`](../../lifeostomanyagent/server/overlays/pi_tools.md)，仅 `connector_id=pi` 时注入。

## Inspector API

Web Console 使用只读 Inspector API 查看一个 World 的聚合运行时状态：

```http
GET /inspector/worlds/{world_id}/state?limit=100
```

该接口需要 `X-API-Key`，不修改 runtime state。`limit` 默认 100，最大 500。

响应包含：

- `world`：WorldInstance 基础信息。
- `pack`：关联 Agent Pack。
- `persona`：`runtime_state_documents` 中 `persona` 模块的 JSON，缺失时为 `null`。
- `emotion`：`runtime_state_documents` 中 `emotion` 模块的 JSON，缺失时为 `null`。
- `memories`：用户记忆列表，按更新时间倒序。
- `dreams`：dream seeds 与 dream records。
- `world_facts`：active/all facts、fact events、clock events、venue visits。

World 不存在时返回 404。

## 自定义 Pack（结构化）

`POST /packs` 推荐使用结构化字段，无需 40KB markdown：

```json
{
  "pack_id": "my-agent",
  "display_name": "我的助手",
  "identity": {
    "agent_name": "小蓝",
    "backstory": "……",
    "relationship_stance": "……"
  },
  "behavior_profile": {
    "speech_style": ["说话简短"],
    "forbidden_patterns": ["不用 emoji"]
  },
  "behavior_trajectory": {
    "reaction_patterns": ["对方说累时先关心"]
  },
  "world_rules": {
    "timezone": "Asia/Shanghai",
    "locations": ["上海"]
  }
}
```

仍支持 legacy `base_system_prompt` 字符串（迁移期兼容）。

## Connector 推荐方式

| Runtime | 方式 |
|---------|------|
| pi CLI | [`pi-connector.md`](../pi-connector.md) |
| pi 桌面客户端 | 待实现：Electron + `systemContext` |
| Claude Code | [`claude-code-connector.md`](../claude-code-connector.md) |
| Codex | [`codex-connector.md`](../codex-connector.md) |
| Hermes | [`hermes-connector.md`](../hermes-connector.md) |
| OpenClaw | [`openclaw-connector.md`](../openclaw-connector.md) |

Hook 模板见 [`connectors/templates/`](../../connectors/templates/)。

## 环境变量

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | SQLAlchemy 连接串；默认 `{LIFEOS_DATA_ROOT}/lifeos.sqlite3`，可设置为 PostgreSQL |
| `REDIS_URL` | Redis context 短缓存（可选；未配置时不影响核心功能） |
| `LIFEOS_API_KEY` | API Key |
| `LIFEOS_DATA_ROOT` | SQLite 默认位置、旧 runtime 文件迁移来源和非核心产物目录 |

数据库表结构与 JSON 字段说明见 [`docs/database.md`](../database.md)。

## CLI

```bash
lifeos login --server http://127.0.0.1:8000 --api-key ...
lifeos world-create --pack chenyuan --name "我的陈远"
lifeos context "你好" --connector pi
lifeos connector install pi
lifeos session-start --connector pi --session-id abc
```
