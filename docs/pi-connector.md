# pi agent × LifeOS 安装与卸载

本文说明如何在 [pi coding agent](https://github.com/badlogic/pi-mono)（`pi` CLI）中接入 LifeOS（Alice 世界状态、人设、情绪、记忆），以及如何验证、停用与卸载。

> **说明**：本文档针对 **pi CLI + Extension** 联动。Alice Electron 桌面端通过子进程接入 pi 的方案见 [`docs/api/pi-agent-adapter.md`](api/pi-agent-adapter.md)，与 LifeOS Extension 可并存，但集成路径不同。

## 前置条件

| 项 | 要求 |
|----|------|
| pi | 已安装 `pi` 命令，且支持用户 Extension（`~/.pi/agent/extensions/`） |
| Node.js | pi 运行环境需支持 `fetch`（Node 18+ 或 pi 自带运行时） |
| LifeOS 服务 | 本地或自托管 API 可访问（默认 `http://127.0.0.1:8000`） |
| `lifeos` CLI | 在 `lifeostomanyagent` 目录执行 `uv sync` 后可用 |

LifeOS 服务端启动示例：

```bash
cd lifeostomanyagent
docker compose up -d postgres redis
uv run uvicorn lifeostomanyagent.server.main:app --reload --port 8000
```

## 架构简述

LifeOS 通过 **pi TypeScript Extension** 在每轮 agent 启动前合并 system prompt：

```
pi 用户发送消息
    → before_agent_start（Extension）
         首次该 session → POST /runtime/session/start
         每轮           → POST /runtime/context
                         → injected=true 时 POST /runtime/turn/begin
                         → injected=true 时返回 systemPrompt = LifeOS 块 + pi 原 system
    → agent_end        → 若本轮已注入则 POST /runtime/turn/finish
    → session_shutdown → POST /runtime/session/end
```

与 Claude Code / Hermes 的差异：

| 运行时 | Context 注入位置 |
|--------|------------------|
| **pi** | 合并进 **system prompt**（`before_agent_start`） |
| Claude Code | `UserPromptSubmit` → `additionalContext` |
| Hermes | `pre_llm_call` → 追加到 **user message** |

- Extension 文件：`~/.pi/agent/extensions/lifeos.ts`
- 配置：`~/.lifeos/config.json`（与 `lifeos login` 共用）
- `connector_id` 固定为 `pi`
- 会话内斜杠命令：`/lifeos` — 检查连接与 world 状态

源码：[`connectors/pi/lifeos.ts`](../connectors/pi/lifeos.ts)

---

## 一、安装流程

### 1. 配置 LifeOS 客户端

```bash
cd lifeostomanyagent
uv run lifeos login --server http://127.0.0.1:8000 --api-key <你的 API Key>
uv run lifeos world-create --pack alice --name "我的 Alice"
```

确认 `~/.lifeos/config.json` 含 `server_url`、`api_key`、`default_world_id`。

可选在 `config.json` 中设置合并方式（默认 `prepend`）：

```json
{
  "server_url": "http://127.0.0.1:8000",
  "api_key": "your-key",
  "default_world_id": "uuid",
  "merge_mode": "prepend"
}
```

- `prepend`：LifeOS 块在前，pi 原 system 在后（默认，Alice 人设优先）
- `append`：pi 原 system 在前，LifeOS 块在后

### 2. 安装 pi Extension

```bash
uv run lifeos connector install pi
```

**安装结果：**

| 操作 | 路径 |
|------|------|
| 复制或链接 Extension | `~/.pi/agent/extensions/lifeos.ts` |

pi 会在启动时自动加载 `extensions` 目录下的 `.ts` 文件，**无需**像 Hermes 那样单独 `enable`。

**开发模式**（改仓库内源码立即生效）：

```bash
uv run lifeos connector install pi --symlink
```

**自定义 extensions 目录**（少见）：

```bash
uv run lifeos connector install pi --extensions-dir /path/to/extensions
```

### 3. 启动 pi

```bash
pi
```

新开一个 pi 会话即可；若 pi 已在运行，建议退出后重新启动以加载新 Extension。

### 4. 检查 Extension 是否加载（可选）

在 pi 会话中输入：

```
/lifeos
```

- 成功：通知显示 `LifeOS 已连接 world=xxxxxxxx… merge=prepend`
- 未配置：提示运行 `lifeos login && lifeos world-create`
- 服务不可达：显示 `LifeOS 服务不可达`

---

## 二、环境变量（可选）

除 `~/.lifeos/config.json` 外，可用环境变量覆盖（便于 CI 或多环境）：

| 变量 | 说明 |
|------|------|
| `LIFEOS_ENABLED` | 设为 `false` 时禁用 Extension（不删文件） |
| `LIFEOS_SERVER_URL` | API 地址 |
| `LIFEOS_API_KEY` | API Key |
| `LIFEOS_WORLD_ID` | 世界 ID |
| `LIFEOS_MERGE_MODE` | `prepend` 或 `append` |

示例（临时禁用，不卸载）：

```bash
LIFEOS_ENABLED=false pi
```

---

## 三、验证是否安装成功

### 层 1：LifeOS API（不依赖 pi）

```bash
curl -s http://127.0.0.1:8000/health
uv run lifeos context "你好，测试一下" --connector pi
```

输出应含 Alice 人设相关片段。

### 层 2：确认 Extension 文件

```bash
ls -la ~/.pi/agent/extensions/lifeos.ts
head -20 ~/.pi/agent/extensions/lifeos.ts
```

应能看到 `LifeOS pi Extension`、`before_agent_start` 等字样。

### 层 3：pi 端到端

1. 确认 LifeOS API 在跑、`config.json` 正确
2. 运行 `pi`，执行 `/lifeos` 确认已连接
3. 发送例如：「你是谁？你现在在哪里？」
4. 若回答体现 Alice 人设，则注入成功

若拉取失败，pi 会通知「LifeOS context 拉取失败，使用 pi 默认 system prompt」，此时检查服务与 `default_world_id`。

### 常见问题

| 现象 | 处理 |
|------|------|
| `/lifeos` 提示未配置 | `lifeos login` + `lifeos world-create` |
| 仍是通用助手 | Extension 未安装到正确目录；重启 `pi` |
| context 拉取失败 | API 未启动、Key 错误、防火墙 |
| `pi --init-only` 挂起 | 已知现象，用正常 `pi` 会话测试即可 |
| TypeScript 报错 | 确认 pi 版本支持 Extension API（`@earendil-works/pi-coding-agent`） |

---

## 四、卸载流程

当前 **没有** `lifeos connector uninstall pi` 命令，请按下面手动操作。

### 方式 A：删除 Extension 文件（推荐，彻底卸载）

```bash
rm -f ~/.pi/agent/extensions/lifeos.ts
```

若曾 `--symlink` 安装，上述命令只删除链接，不删仓库源码。

删除后**重启 pi**，Extension 即不再加载。

### 方式 B：临时禁用（保留文件）

不重命名文件，仅用环境变量：

```bash
LIFEOS_ENABLED=false pi
```

或在 shell 配置中 `export LIFEOS_ENABLED=false`。恢复时取消该变量即可。

### 方式 C：重命名 Extension（快速停用）

```bash
mv ~/.pi/agent/extensions/lifeos.ts ~/.pi/agent/extensions/lifeos.ts.off
```

恢复：

```bash
mv ~/.pi/agent/extensions/lifeos.ts.off ~/.pi/agent/extensions/lifeos.ts
```

重启 `pi` 后生效。

### 方式 D：重装（覆盖）

无需先卸载：

```bash
uv run lifeos connector install pi
```

会覆盖 `~/.pi/agent/extensions/lifeos.ts`。

### 关于 `~/.lifeos/config.json`

卸载 pi Extension **不必** 删除此文件；Claude Code、Codex、Hermes 等仍可能使用。

---

## 五、与其它 Connector 的关系

| Connector | 安装产物 | 共用 config |
|-----------|----------|-------------|
| pi | `~/.pi/agent/extensions/lifeos.ts` | `~/.lifeos/config.json` |
| Claude Code / Codex | `~/.lifeos/hooks/lifeos_hook.py` + 各自 settings | 同上 |
| Hermes | `~/.hermes/plugins/lifeos/` | 同上 |

多个 Connector 可同时安装，共用同一 `default_world_id` 时 **world 状态一致**（persona、emotion、memory 等同一份数据）。

---

## 六、文件路径速查

| 路径 | 说明 |
|------|------|
| `~/.pi/agent/extensions/lifeos.ts` | 已安装的 pi Extension |
| `~/.lifeos/config.json` | LifeOS 客户端配置 |
| `lifeostomanyagent/connectors/pi/lifeos.ts` | 仓库内 Extension 源码 |
| `lifeostomanyagent/data/worlds/<world_id>/` | 世界运行时状态 |

---

## 七、与 API 文档的关系

- 平台 API 总览：[`docs/api/lifeos-platform.md`](api/lifeos-platform.md)
- Claude Code：[`docs/claude-code-connector.md`](claude-code-connector.md)
- Hermes：[`docs/hermes-connector.md`](hermes-connector.md)
- Alice × pi 子进程协议（Electron）：[`docs/api/pi-agent-adapter.md`](api/pi-agent-adapter.md)
