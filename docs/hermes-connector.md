# Hermes Agent × LifeOS 安装与卸载

本文说明如何在 [Hermes Agent](https://hermes-agent.nousresearch.com/) 中接入 LifeOS（Alice 世界状态、人设、情绪、记忆），以及如何验证、停用与卸载。

## 前置条件

| 项 | 要求 |
|----|------|
| Hermes | 已安装且 `hermes` 命令可用 |
| LifeOS 服务 | 本地或自托管 API 可访问（默认 `http://127.0.0.1:8000`） |
| `lifeos` CLI | 在 `lifeostomanyagent` 目录执行 `uv sync` 后可用 |

LifeOS 服务端启动示例：

```bash
cd lifeostomanyagent
docker compose up -d postgres redis
uv run uvicorn lifeostomanyagent.server.main:app --reload --port 8000
```

## 架构简述

LifeOS 通过 **Hermes Python Plugin**（非 Shell hook）在每轮对话前注入 context：

```
Hermes 用户消息
    → on_session_start     → POST /runtime/session/start
    → pre_llm_call         → POST /runtime/context
                         → injected=true 时 POST /runtime/turn/begin
                         → injected=true 时返回 {"context": "..."} 追加到 user message
    → post_llm_call        → 若本轮已注入则 POST /runtime/turn/finish
    → on_session_end       → POST /runtime/session/end
```

插件读取 `~/.lifeos/config.json`（与 Claude Code / Codex 共用），`connector_id` 固定为 `hermes`。

源码目录：[`connectors/hermes/`](../connectors/hermes/)

---

## 一、安装流程

### 1. 配置 LifeOS 客户端

```bash
cd lifeostomanyagent
uv run lifeos login --server http://127.0.0.1:8000 --api-key <你的 API Key>
uv run lifeos world-create --pack alice --name "我的 Alice"
```

确认 `~/.lifeos/config.json` 含 `server_url`、`api_key`、`default_world_id`。

如果已经有多个 World，可以随时切换 Hermes 默认使用的 World：

```bash
uv run lifeos world-list
uv run lifeos world-use --pack musheng
```

也可以用名称或精确 world_id：

```bash
uv run lifeos world-use --name "木生"
uv run lifeos world-use --world-id c93f2ac7-72a0-4a33-97f7-50c2b06a0280
```

`world-use` 会更新 `~/.lifeos/config.json` 的 `default_world_id`。切换后重启 Hermes，让插件重新读取配置。

### 2. 安装 Hermes 插件

```bash
uv run lifeos connector install hermes
```

**安装结果：**

- 将插件复制到 `~/.hermes/plugins/lifeos/`
- 包含 `plugin.yaml`、`__init__.py`、`lifeos_client.py`

**开发模式**（改源码立即生效，无需重复 install）：

```bash
uv run lifeos connector install hermes --symlink
```

此时 `~/.hermes/plugins/lifeos` 为指向仓库内 `connectors/hermes/` 的符号链接。

**自定义插件目录**（少见）：

```bash
uv run lifeos connector install hermes --hermes-plugins-dir /path/to/plugins
```

### 3. 在 Hermes 中启用插件（必做）

Hermes 插件默认 **opt-in**，仅复制文件不会自动加载。

```bash
hermes plugins enable lifeos
```

或交互式：

```bash
hermes plugins
# 在列表中将 lifeos 设为 enabled
```

也可手动编辑 `~/.hermes/config.yaml`：

```yaml
plugins:
  enabled:
  - lifeos          # 加入此项
  disabled: []
```

### 4. 重启 Hermes

启用或重装插件后，需**退出并重新启动** `hermes`，新 hook 才会生效。

### 5. 确认 Hermes 已识别插件

```bash
hermes plugins list | grep lifeos
```

期望：`lifeos` 状态为 **enabled**（若仍为 `not enabled`，回到步骤 3）。

---

## 二、验证是否安装成功

### 层 1：LifeOS API（不依赖 Hermes）

```bash
curl -s http://127.0.0.1:8000/health
uv run lifeos context "你好，测试一下" --connector hermes
```

输出应含 Alice 人设相关片段（如「白艾莉」「横琴」等）。

### 层 2：插件 client（不启动 Hermes UI）

```bash
python3 <<'EOF'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".hermes/plugins/lifeos"))
import lifeos_client

ctx = lifeos_client.fetch_context("hermes", "test-session", "你好")
if ctx and len(ctx) > 100:
    print("OK — context 长度:", len(ctx))
    print(ctx[:400], "...")
else:
    print("失败 — 检查 ~/.lifeos/config.json 与 LifeOS 服务")
EOF
```

### 层 3：Hermes 端到端

1. 确认 `hermes plugins list` 中 `lifeos` 为 **enabled**
2. 运行 `hermes`，发送例如：「你是谁？你现在在哪里？」
3. 若回答体现 Alice 人设（非通用助手口吻），则注入成功

### 常见问题

| 现象 | 处理 |
|------|------|
| `plugins list` 显示 `not enabled` | `hermes plugins enable lifeos` 后重启 Hermes |
| context 为空 | 检查 `default_world_id`、`lifeos login`、API 是否在跑 |
| 回答仍是通用助手 | 插件未 enable 或未重启 Hermes |
| 连接超时 | 确认 `server_url` 与防火墙/端口 |

---

## 三、卸载流程

当前 **没有** `lifeos connector uninstall hermes` 命令，请按下面手动操作。

### 方式 A：仅停用（保留文件，推荐先试）

不再注入 LifeOS，但插件目录仍在：

```bash
hermes plugins disable lifeos
```

或从 `~/.hermes/config.yaml` 的 `plugins.enabled` 中删除 `lifeos`，然后重启 Hermes。

验证：

```bash
hermes plugins list | grep lifeos
# 应为 not enabled
```

### 方式 B：删除插件文件（彻底移除）

在已停用（方式 A）的前提下：

```bash
rm -rf ~/.hermes/plugins/lifeos
```

若曾使用 `--symlink` 安装，上述命令只删除符号链接，不会删除仓库源码。

### 方式 C：重装（覆盖安装）

无需先卸载，直接再次 install 会覆盖/重建 `~/.hermes/plugins/lifeos`：

```bash
uv run lifeos connector install hermes
```

### 关于 `~/.lifeos/config.json`

卸载 Hermes 插件 **不必** 删除此文件；Claude Code、Codex、pi 等 connector 仍可能使用。仅当不再使用任何 LifeOS connector 时，可自行决定是否删除。

---

## 四、文件路径速查

| 路径 | 说明 |
|------|------|
| `~/.hermes/plugins/lifeos/` | 已安装的 Hermes 插件 |
| `~/.hermes/config.yaml` | Hermes 配置（`plugins.enabled` 含 `lifeos` 时才会加载） |
| `~/.lifeos/config.json` | LifeOS 客户端配置（API、world_id） |
| `lifeostomanyagent/connectors/hermes/` | 仓库内插件源码 |
| `lifeostomanyagent/data/worlds/<world_id>/` | 世界运行时状态（persona、emotion 等） |

---

## 五、与 API 文档的关系

- 平台 API 与 Hook 映射总览：[`docs/api/lifeos-platform.md`](api/lifeos-platform.md)
- 本文专注 Hermes 的安装、启用、验证与卸载操作步骤
