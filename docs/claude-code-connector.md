# Claude Code × LifeOS 安装与卸载

本文说明如何在 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 中接入 LifeOS（陈远世界状态、人设、情绪、记忆），以及如何验证、停用与卸载。

## 前置条件

| 项 | 要求 |
|----|------|
| Claude Code | 已安装且支持 [Hooks](https://docs.anthropic.com/en/docs/claude-code/hooks) |
| LifeOS 服务 | 本地或自托管 API 可访问（默认 `http://127.0.0.1:8000`） |
| `lifeos` CLI | 在 `lifeostomanyagent` 目录执行 `uv sync` 后可用 |
| Python | 安装 hook 时使用的解释器需能运行 `urllib`（建议用 `uv run lifeos connector install`，见下文） |

LifeOS 服务端启动示例：

```bash
cd lifeostomanyagent
docker compose up -d
uv run uvicorn lifeostomanyagent.server.main:app --reload --port 8000
```

默认使用 SQLite（`LIFEOS_DATA_ROOT` 下的 `lifeos.sqlite3`）；PostgreSQL / Redis 仅在需要时通过 compose profile 和环境变量启用。

## 架构简述

LifeOS 通过 **Claude Code Command Hook** 在会话生命周期中调用统一脚本 `lifeos_hook.py`：

```
Claude Code 事件
    → SessionStart        → lifeos_hook.py session-start claude-code
                         → POST /runtime/session/start
    → UserPromptSubmit  → lifeos_hook.py user-prompt-submit claude-code
                         → POST /runtime/context
                         → injected=true 时 POST /runtime/turn/begin
                         → injected=true 时 stdout: hookSpecificOutput.additionalContext
    → Stop                → lifeos_hook.py stop claude-code
                         → 若本轮已注入则 POST /runtime/turn/finish
    → SessionEnd          → lifeos_hook.py session-end claude-code
                         → POST /runtime/session/end
```

- 配置写入：`~/.claude/settings.json` 的 `hooks` 字段
- Hook 脚本：`~/.lifeos/hooks/lifeos_hook.py`（与 Codex **共用** 同一份脚本，参数 `connector_id` 区分运行时）
- 客户端配置：`~/.lifeos/config.json`，`connector_id` 为 `claude-code`

Hook 源码模板：[`connectors/templates/lifeos_hook.py`](../connectors/templates/lifeos_hook.py)

---

## 一、安装流程

### 1. 配置 LifeOS 客户端

```bash
cd lifeostomanyagent
uv run lifeos login --server http://127.0.0.1:8000 --api-key <你的 API Key>
uv run lifeos world-create --pack chenyuan --name "我的陈远"
```

确认 `~/.lifeos/config.json` 含 `server_url`、`api_key`、`default_world_id`。

### 2. 安装 Claude Code hooks

**推荐**在 `lifeostomanyagent` 目录用 `uv run`，这样 `settings.json` 里记录的 Python 路径指向当前 venv，避免找不到依赖：

```bash
uv run lifeos connector install claude-code
```

**安装结果：**

| 操作 | 路径 |
|------|------|
| 复制/链接 hook 脚本 | `~/.lifeos/hooks/lifeos_hook.py` |
| 合并 hooks 配置 | `~/.claude/settings.json` |

写入的 Claude Code 事件：

| Claude Code 事件 | Hook 命令参数 | 超时 |
|------------------|---------------|------|
| `SessionStart` | `session-start claude-code` | 30s |
| `UserPromptSubmit` | `user-prompt-submit claude-code` | 30s（状态栏：LifeOS context） |
| `Stop` | `stop claude-code` | 15s |
| `SessionEnd` | `session-end claude-code` | 15s |

若已存在旧的 LifeOS hook 项，安装会**替换**同事件中指向 `lifeos_hook.py` 的条目，其它 hook 保留。

**开发模式**（改模板立即生效）：

```bash
uv run lifeos connector install claude-code --symlink
```

**自定义 settings 路径**（少见）：

```bash
uv run lifeos connector install claude-code --claude-settings /path/to/settings.json
```

### 3. 重启 Claude Code

安装或修改 `settings.json` 后，**退出并重新打开** Claude Code（或新开终端会话中的 `claude`），hooks 才会加载。

### 4. 在 Claude Code 中确认 hooks（可选）

在 Claude Code 内执行：

```
/hooks
```

应能看到包含 `lifeos_hook.py` 且参数含 `claude-code` 的条目。

---

## 二、验证是否安装成功

### 层 1：LifeOS API（不依赖 Claude Code）

```bash
curl -s http://127.0.0.1:8000/health
uv run lifeos context "你好，测试一下" --connector claude-code
```

输出应含 陈远人设相关片段。

### 层 2：直接调用 hook 脚本

模拟 `UserPromptSubmit`（需 LifeOS 服务与 `config.json` 已配置）：

```bash
echo '{"session_id":"hook-test-1","prompt":"你好"}' | \
  python3 ~/.lifeos/hooks/lifeos_hook.py user-prompt-submit claude-code
```

成功时 stdout 为 JSON，且 `hookSpecificOutput.additionalContext` 非空。无输出或为空时，检查 API 与 `default_world_id`。

也可用仓库内冒烟脚本（需先 `uv sync`）：

```bash
cd lifeostomanyagent
uv run python connectors/templates/test_hook_smoke.py
```

### 层 3：Claude Code 端到端

1. 确认 LifeOS API 在跑、`~/.lifeos/config.json` 正确
2. 启动 `claude`，发送例如：「你是谁？你现在在哪里？」
3. 提交提示时状态栏可能出现 **LifeOS context**（`UserPromptSubmit` hook）
4. 若回答体现 陈远人设，则注入成功

### 常见问题

| 现象 | 处理 |
|------|------|
| 无 additionalContext | `lifeos login` / `world-create` 未做，或服务未启动 |
| Hook 不执行 | 未重启 Claude Code；检查 `settings.json` 是否含 `hooks` |
| Python 找不到 | 用 `uv run lifeos connector install claude-code` 重装，或改 command 为绝对路径 |
| 与 Codex 冲突 | 共用 `lifeos_hook.py`，仅 `settings.json` / `hooks.json` 中 connector 参数不同，可并存 |

---

## 三、卸载流程

当前 **没有** `lifeos connector uninstall claude-code` 命令，请按下面手动操作。

### 方式 A：在 Claude Code 内删除（推荐）

1. 打开 Claude Code，执行 `/hooks`
2. 删除所有 command 中含 `lifeos_hook.py` 且含 `claude-code` 的项
3. 重启 Claude Code

### 方式 B：编辑 settings.json

编辑 `~/.claude/settings.json`（或你安装时指定的 `--claude-settings` 路径）：

1. 找到 `hooks` 对象下的 `SessionStart`、`UserPromptSubmit`、`Stop`、`SessionEnd`
2. 在每个事件的 `hooks` 数组中，删除 `command` 字段包含 `lifeos_hook.py` 的项
3. 若某事件下 `hooks` 为空，可保留空数组或删除该事件键
4. 保存后重启 Claude Code

**识别 LifeOS hook 的特征：** `command` 字符串中包含 `lifeos_hook.py` 和 `claude-code`。

### 方式 C：临时停用（不删配置）

不重命名或删除 `settings.json`，仅让脚本不可执行：

```bash
mv ~/.lifeos/hooks/lifeos_hook.py ~/.lifeos/hooks/lifeos_hook.py.off
```

恢复：

```bash
mv ~/.lifeos/hooks/lifeos_hook.py.off ~/.lifeos/hooks/lifeos_hook.py
chmod +x ~/.lifeos/hooks/lifeos_hook.py
```

Claude Code 仍会尝试调用 hook，但会失败；建议最终用方式 A/B 清理配置。

### 方式 D：删除 hook 脚本（注意 Codex）

若 **仅** 使用 Claude Code、未安装 Codex hooks，可删除脚本：

```bash
rm -f ~/.lifeos/hooks/lifeos_hook.py
```

若已 `uv run lifeos connector install codex`，**不要删除**该脚本，否则 Codex 也会失效；只从 `~/.claude/settings.json` 移除 hooks 即可。

### 方式 E：重装（覆盖）

无需先卸载，直接再次 install 会覆盖脚本并重新合并 `settings.json` 中的 LifeOS 项：

```bash
uv run lifeos connector install claude-code
```

### 关于 `~/.lifeos/config.json`

卸载 Claude Code hooks **不必** 删除此文件；Hermes、pi、Codex 等仍可能使用。

---

## 四、与 Codex 的关系

Claude Code 与 Codex 使用**同一份** `~/.lifeos/hooks/lifeos_hook.py`，区别仅在于：

| 运行时 | 配置文件 | connector 参数 |
|--------|----------|----------------|
| Claude Code | `~/.claude/settings.json` | `claude-code` |
| Codex | `~/.codex/hooks.json` | `codex` |

先装 Claude Code 再装 Codex（或反之）不会互相覆盖脚本，只会各自写入自己的 settings。

---

## 五、文件路径速查

| 路径 | 说明 |
|------|------|
| `~/.claude/settings.json` | Claude Code hooks 配置 |
| `~/.lifeos/hooks/lifeos_hook.py` | 统一 hook 脚本（Claude + Codex） |
| `~/.lifeos/config.json` | LifeOS API Key、world_id |
| `lifeostomanyagent/connectors/templates/lifeos_hook.py` | 仓库内模板源码 |
| `lifeostomanyagent/data/worlds/<world_id>/` | 世界运行时状态 |

---

## 六、与 API 文档的关系

- 平台 API 总览：[`docs/api/lifeos-platform.md`](api/lifeos-platform.md)
- Hermes 安装/卸载：[`docs/hermes-connector.md`](hermes-connector.md)
- Codex：[`docs/codex-connector.md`](codex-connector.md)
