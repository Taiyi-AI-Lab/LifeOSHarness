# Codex × LifeOS 安装与卸载

本文说明如何在 [OpenAI Codex](https://developers.openai.com/codex) CLI 中接入 LifeOS（Alice 世界状态、人设、情绪、记忆），以及如何验证、停用与卸载。

Codex 与 Claude Code 使用**同一套** LifeOS hook 脚本与事件模型，仅配置文件与 `connector_id` 不同。Claude Code 侧说明见 [`claude-code-connector.md`](claude-code-connector.md)。

## 前置条件

| 项 | 要求 |
|----|------|
| Codex CLI | 已安装且支持 Hooks（`config.toml` 中 `[features] hooks = true`） |
| LifeOS 服务 | 本地或自托管 API 可访问（默认 `http://127.0.0.1:8000`） |
| `lifeos` CLI | 在 `lifeostomanyagent` 目录执行 `uv sync` 后可用 |
| Python | 安装 hook 时使用的解释器需能运行 `urllib`（建议 `uv run lifeos connector install codex`） |

LifeOS 服务端启动示例：

```bash
cd lifeostomanyagent
docker compose up -d postgres redis
uv run uvicorn lifeostomanyagent.server.main:app --reload --port 8000
```

## 架构简述

LifeOS 通过 **Codex Command Hook** 调用统一脚本 `lifeos_hook.py`（与 Claude Code 共用）：

```
Codex 事件（与 Claude Code 同名）
    → SessionStart        → lifeos_hook.py session-start codex
                         → POST /runtime/session/start
    → UserPromptSubmit  → lifeos_hook.py user-prompt-submit codex
                         → POST /runtime/turn/begin
                         → POST /runtime/context
                         → stdout: hookSpecificOutput.additionalContext
    → Stop                → lifeos_hook.py stop codex
                         → POST /runtime/turn/finish
    → SessionEnd          → lifeos_hook.py session-end codex
                         → POST /runtime/session/end
```

| 项 | 路径 / 值 |
|----|-----------|
| Hook 配置 | `$CODEX_HOME/hooks.json`（默认 `~/.codex/hooks.json`） |
| 启用 hooks | `$CODEX_HOME/config.toml` → `[features]` → `hooks = true` |
| Hook 脚本 | `~/.lifeos/hooks/lifeos_hook.py`（与 Claude Code **共用**） |
| LifeOS 客户端 | `~/.lifeos/config.json` |
| connector_id | `codex` |

Hook 模板：[`connectors/templates/lifeos_hook.py`](../connectors/templates/lifeos_hook.py)

---

## 一、安装流程

### 1. 配置 LifeOS 客户端

```bash
cd lifeostomanyagent
uv run lifeos login --server http://127.0.0.1:8000 --api-key <你的 API Key>
uv run lifeos world-create --pack alice --name "我的 Alice"
```

确认 `~/.lifeos/config.json` 含 `server_url`、`api_key`、`default_world_id`。

### 2. 安装 Codex hooks

**推荐**在 `lifeostomanyagent` 目录执行，使 `hooks.json` 中的 Python 路径指向当前 venv：

```bash
uv run lifeos connector install codex
```

**安装结果：**

| 操作 | 默认路径 |
|------|----------|
| 复制/链接 hook 脚本 | `~/.lifeos/hooks/lifeos_hook.py` |
| 合并 hooks 配置 | `~/.codex/hooks.json` |
| 启用 Codex hooks 功能 | `~/.codex/config.toml` 写入或补全 `[features]` → `hooks = true` |

写入的 Codex 事件（与 Claude Code 相同的事件名）：

| Codex 事件 | Hook 命令参数 | 超时 |
|------------|---------------|------|
| `SessionStart` | `session-start codex` | 30s |
| `UserPromptSubmit` | `user-prompt-submit codex` | 30s（`statusMessage`: LifeOS context） |
| `Stop` | `stop codex` | 15s |
| `SessionEnd` | `session-end codex` | 15s |

若同一事件中已有旧的 LifeOS hook，安装会**替换**含 `lifeos_hook.py` 的条目，其它 hook 保留。

**开发模式**（改模板立即生效）：

```bash
uv run lifeos connector install codex --symlink
```

**自定义 Codex 目录**（`CODEX_HOME` 非默认时）：

```bash
export CODEX_HOME=/path/to/.codex
uv run lifeos connector install codex --codex-home /path/to/.codex
```

或安装时显式指定：

```bash
uv run lifeos connector install codex --codex-home /path/to/.codex
```

### 3. 确认 config.toml 已启用 hooks

安装程序会自动在 `config.toml` 中设置 `hooks = true`。可手动检查：

```bash
grep -A2 '\[features\]' ~/.codex/config.toml
# 应包含: hooks = true
```

若仍为 `hooks = false`，Codex 不会执行 `hooks.json` 中的命令。

### 4. 重启 Codex

修改 `hooks.json` 或 `config.toml` 后，**退出并重新启动** `codex` 会话，hooks 才会加载。

---

## 二、验证是否安装成功

### 层 1：LifeOS API（不依赖 Codex）

```bash
curl -s http://127.0.0.1:8000/health
uv run lifeos context "你好，测试一下" --connector codex
```

输出应含 Alice 人设相关片段。

### 层 2：确认配置文件

```bash
ls -la ~/.lifeos/hooks/lifeos_hook.py
cat ~/.codex/hooks.json | grep lifeos_hook
grep 'hooks' ~/.codex/config.toml
```

`hooks.json` 中应出现 `lifeos_hook.py` 且命令行含 **`codex`**（不是 `claude-code`）。

### 层 3：直接调用 hook 脚本

模拟 `UserPromptSubmit`：

```bash
echo '{"session_id":"hook-test-1","prompt":"你好"}' | \
  python3 ~/.lifeos/hooks/lifeos_hook.py user-prompt-submit codex
```

成功时 stdout 为 JSON，且 `hookSpecificOutput.additionalContext` 非空。

仓库内冒烟脚本默认测 `claude-code`，测 Codex 可改为：

```bash
echo '{"session_id":"hook-test-1","prompt":"你好"}' | \
  uv run python ~/.lifeos/hooks/lifeos_hook.py user-prompt-submit codex
```

### 层 4：Codex 端到端

1. 确认 LifeOS API 在跑、`config.json` 正确、`hooks = true`
2. 启动 `codex`，发送例如：「你是谁？你现在在哪里？」
3. 若回答体现 Alice 人设，则注入成功

### 常见问题

| 现象 | 处理 |
|------|------|
| Hook 完全不执行 | 检查 `config.toml` 中 `hooks = true`；重启 Codex |
| 无 additionalContext | `lifeos login` / `world-create`；确认服务已启动 |
| 命令含 claude-code | 重装：`uv run lifeos connector install codex` |
| Python 找不到 | 用 `uv run lifeos connector install codex` 重装 |
| 与 Claude Code 并存 | 共用 `lifeos_hook.py`，各自 `hooks.json` / `settings.json`，可同时安装 |

---

## 三、卸载流程

当前 **没有** `lifeos connector uninstall codex` 命令，请按下面手动操作。

### 方式 A：编辑 hooks.json（推荐）

编辑 `~/.codex/hooks.json`（或 `$CODEX_HOME/hooks.json`）：

1. 在 `hooks` 下找到 `SessionStart`、`UserPromptSubmit`、`Stop`、`SessionEnd`
2. 删除每个事件中 `command` 含 `lifeos_hook.py` 且含 **`codex`** 的项
3. 保存后重启 Codex

**识别特征：** `lifeos_hook.py` + 参数 `codex`（如 `... lifeos_hook.py user-prompt-submit codex`）。

### 方式 B：临时停用 hook 脚本（影响 Claude Code）

若 Claude Code 也在用同一脚本，不要删除文件，仅重命名：

```bash
mv ~/.lifeos/hooks/lifeos_hook.py ~/.lifeos/hooks/lifeos_hook.py.off
```

仅卸载 Codex 时更宜用方式 A，保留脚本供 Claude Code 使用。

### 方式 C：关闭 Codex hooks 功能（可选）

若不再需要任何 Codex hook，可在 `config.toml` 中设置：

```toml
[features]
hooks = false
```

这会影响**所有** Codex hooks，不仅是 LifeOS。若你仍需要其它 hook，保持 `hooks = true`，只用方式 A 删除 LifeOS 项。

### 方式 D：删除 hook 脚本（仅当未用 Claude Code）

```bash
rm -f ~/.lifeos/hooks/lifeos_hook.py
```

若已安装 Claude Code LifeOS hooks，**不要删除**该文件。

### 方式 E：重装（覆盖）

```bash
uv run lifeos connector install codex
```

会覆盖 `lifeos_hook.py`（若未用 `--symlink`）并重新合并 `hooks.json` 中的 LifeOS 项。

### 关于 `~/.lifeos/config.json`

卸载 Codex hooks **不必** 删除；pi、Hermes、OpenClaw 等仍可能使用。

---

## 四、与 Claude Code 的关系

| 运行时 | 配置文件 | connector 参数 |
|--------|----------|----------------|
| Codex | `~/.codex/hooks.json` + `~/.codex/config.toml` | `codex` |
| Claude Code | `~/.claude/settings.json` | `claude-code` |

- **共用** `~/.lifeos/hooks/lifeos_hook.py`
- 先装 Codex 再装 Claude（或反之）只各自更新自己的 JSON/TOML，**不会**互相覆盖脚本
- 再次 `install codex` 只会替换 `hooks.json` 里 LifeOS 相关项，不影响 Claude 的 `settings.json`

---

## 五、文件路径速查

| 路径 | 说明 |
|------|------|
| `~/.codex/hooks.json` | Codex hooks 配置 |
| `~/.codex/config.toml` | Codex 功能开关（`hooks = true`） |
| `$CODEX_HOME` | 默认 `~/.codex`，可环境变量覆盖 |
| `~/.lifeos/hooks/lifeos_hook.py` | 统一 hook 脚本 |
| `~/.lifeos/config.json` | LifeOS API、world_id |
| `lifeostomanyagent/connectors/templates/lifeos_hook.py` | 仓库模板 |
| `lifeostomanyagent/data/worlds/<world_id>/` | 世界运行时状态 |

---

## 六、相关文档

- 平台 API：[`docs/api/lifeos-platform.md`](../../docs/api/lifeos-platform.md)
- Claude Code（同脚本、不同配置）：[`docs/claude-code-connector.md`](claude-code-connector.md)
- pi：[`docs/pi-connector.md`](pi-connector.md)
- Hermes：[`docs/hermes-connector.md`](hermes-connector.md)
- OpenClaw：[`docs/openclaw-connector.md`](openclaw-connector.md)
