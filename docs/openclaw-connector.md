# OpenClaw × LifeOS 安装与卸载

本文说明如何在 [OpenClaw](https://docs.openclaw.ai/) 中接入 LifeOS（Alice 世界状态、人设、情绪、记忆），以及如何验证、停用与卸载。

## 前置条件

| 项 | 要求 |
|----|------|
| OpenClaw | 已安装且 `openclaw` CLI 可用 |
| Node.js | OpenClaw 运行环境（官方建议 Node 22+） |
| LifeOS 服务 | 本地或自托管 API 可访问（默认 `http://127.0.0.1:8000`） |
| `lifeos` CLI | 在 `lifeostomanyagent` 目录执行 `uv sync` 后可用 |

LifeOS 服务端启动示例：

```bash
cd lifeostomanyagent
docker compose up -d postgres redis
uv run uvicorn lifeostomanyagent.server.main:app --reload --port 8000
```

## 架构简述

LifeOS 通过 **OpenClaw 原生 TypeScript Plugin** 在模型调用前合并 system prompt：

```
OpenClaw agent 轮次
    → session_start (reason=new)  → POST /runtime/session/start
    → before_prompt_build         → POST /runtime/context
                                  → injected=true 时 POST /runtime/turn/begin
                                  → injected=true 时返回 systemPrompt（LifeOS 块 + 原 system）
    → agent_end                   → 若本轮已注入则 POST /runtime/turn/finish
    → session_end                 → POST /runtime/session/end
```

与其它 Connector 的注入位置对比：

| 运行时 | Context 注入位置 |
|--------|------------------|
| **OpenClaw** | **system prompt**（`before_prompt_build`） |
| pi | system prompt（`before_agent_start`） |
| Claude Code | `additionalContext` |
| Hermes | user message（`pre_llm_call`） |

- 插件目录：`~/.openclaw/extensions/lifeos/`
- 配置：`~/.lifeos/config.json`，`connector_id` 为 `openclaw`
- 官方文档：[Plugin hooks](https://docs.openclaw.ai/plugins/hooks)、[Plugins](https://docs.openclaw.ai/tools/plugin)

源码：[`connectors/openclaw/`](../connectors/openclaw/)

---

## 一、安装流程

### 1. 配置 LifeOS 客户端

```bash
cd lifeostomanyagent
uv run lifeos login --server http://127.0.0.1:8000 --api-key <你的 API Key>
uv run lifeos world-create --pack alice --name "我的 Alice"
```

确认 `~/.lifeos/config.json` 含 `server_url`、`api_key`、`default_world_id`。

可选 `merge_mode`（与 pi 一致）：

```json
{
  "merge_mode": "prepend"
}
```

- `prepend`：LifeOS 块在前（默认）
- `append`：LifeOS 块在后

### 2. 安装 OpenClaw 插件

**方式 A — LifeOS CLI（推荐）**

```bash
uv run lifeos connector install openclaw
```

安装到 `~/.openclaw/extensions/lifeos/`（含 `openclaw.plugin.json`、`index.ts`、`lifeos-client.ts`、`package.json`）。

**开发模式**：

```bash
uv run lifeos connector install openclaw --symlink
```

**自定义目录**：

```bash
uv run lifeos connector install openclaw --openclaw-extensions-dir /path/to/extensions
```

**方式 B — OpenClaw 自带命令**

```bash
openclaw plugins install --link /path/to/lifeostomanyagent/connectors/openclaw
```

### 3. 启用插件（必做）

Workspace 来源插件默认可能未启用：

```bash
openclaw plugins enable lifeos
```

或在 OpenClaw 配置中：

```json5
{
  plugins: {
    entries: {
      lifeos: { enabled: true },
    },
  },
}
```

若使用 `plugins.allow` 白名单，需包含 `lifeos`。

### 4. 重启 Gateway

安装、启用或改配置后需重启：

```bash
openclaw gateway restart
```

托管 Gateway 在插件变更后可能自动重启；若无响应，请手动执行。

### 5. 验证插件已加载

```bash
openclaw plugins list | grep lifeos
openclaw plugins inspect lifeos --runtime --json
```

应能看到 `before_prompt_build`、`session_start`、`agent_end`、`session_end` 等 hook 注册。

---

## 二、环境变量（可选）

| 变量 | 说明 |
|------|------|
| `LIFEOS_ENABLED` | `false` 时插件不请求 API |
| `LIFEOS_SERVER_URL` | API 地址 |
| `LIFEOS_API_KEY` | API Key |
| `LIFEOS_WORLD_ID` | 世界 ID |
| `LIFEOS_MERGE_MODE` | `prepend` 或 `append` |

---

## 三、验证是否安装成功

### 层 1：LifeOS API

```bash
curl -s http://127.0.0.1:8000/health
uv run lifeos context "你好，测试一下" --connector openclaw
```

### 层 2：确认插件文件

```bash
ls -la ~/.openclaw/extensions/lifeos/
cat ~/.openclaw/extensions/lifeos/openclaw.plugin.json
```

### 层 3：OpenClaw 端到端

1. `openclaw plugins inspect lifeos --runtime --json` 确认 hook 已注册
2. 通过 Gateway / CLI 发起对话，问「你是谁？你现在在哪里？」
3. 回答应体现 Alice 人设

拉取失败时插件**静默降级**（不修改 system prompt），检查 LifeOS 服务与 `config.json`。

### 常见问题

| 现象 | 处理 |
|------|------|
| 列表有插件但 hook 不跑 | `openclaw gateway restart`；`plugins inspect --runtime` |
| 未 enable | `openclaw plugins enable lifeos` |
| context 为空 | `lifeos login` / `world-create` |
| 权限/所有权错误 | Docker 下目录 uid 需与 Gateway 进程一致，见 [官方排障](https://docs.openclaw.ai/tools/plugin) |
| TypeScript 入口报错 | 确认 OpenClaw 版本支持 `openclaw/plugin-sdk/plugin-entry` |

---

## 四、卸载流程

当前 **没有** `lifeos connector uninstall openclaw` 命令。

### 方式 A：OpenClaw 禁用

```bash
openclaw plugins disable lifeos
openclaw gateway restart
```

### 方式 B：删除插件目录

```bash
rm -rf ~/.openclaw/extensions/lifeos
openclaw gateway restart
```

`--symlink` 安装时只删除链接，不删仓库源码。

### 方式 C：临时禁用（保留文件）

```bash
LIFEOS_ENABLED=false openclaw gateway restart
```

### 方式 D：重装

```bash
uv run lifeos connector install openclaw
```

### 关于 `~/.lifeos/config.json`

卸载插件不必删除；其它 Connector 仍可使用。

---

## 五、与其它 Connector 的关系

共用 `~/.lifeos/config.json` 与同一 `default_world_id` 时，**world 状态一致**（persona、emotion、memory 等同一份数据）。

| Connector | 安装产物 |
|-----------|----------|
| OpenClaw | `~/.openclaw/extensions/lifeos/` |
| pi | `~/.pi/agent/extensions/lifeos.ts` |
| Claude / Codex | `~/.lifeos/hooks/lifeos_hook.py` + 各自 settings |
| Hermes | `~/.hermes/plugins/lifeos/` |

---

## 六、文件路径速查

| 路径 | 说明 |
|------|------|
| `~/.openclaw/extensions/lifeos/` | 已安装插件 |
| `~/.openclaw/openclaw.json`（或你的配置路径） | `plugins.entries.lifeos` |
| `~/.lifeos/config.json` | LifeOS 客户端配置 |
| `lifeostomanyagent/connectors/openclaw/` | 仓库源码 |

---

## 七、相关文档

- 平台 API：[`docs/api/lifeos-platform.md`](api/lifeos-platform.md)
- pi：[`docs/pi-connector.md`](pi-connector.md)
- Claude Code：[`docs/claude-code-connector.md`](claude-code-connector.md)
- Hermes：[`docs/hermes-connector.md`](hermes-connector.md)
