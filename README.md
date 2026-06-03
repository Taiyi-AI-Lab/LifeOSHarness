# LifeOS Platform

可定制 Agent 世界的服务端 + `lifeos` 客户端 CLI。Alice 为内置预设 Pack。

## 快速开始

### 1. 启动依赖（Postgres + Redis + API）

```bash
cd lifeostomanyagent
cp .env.example .env
docker compose up -d postgres redis
```

### 2. 安装并启动 API（本地开发）

```bash
uv sync
uv run uvicorn lifeostomanyagent.server.main:app --reload --port 8000
```

### 3. 创建世界并拉 context

```bash
uv run lifeos login --server http://127.0.0.1:8000 --api-key dev-lifeos-key-change-me
uv run lifeos world-create --pack alice --name "我的 Alice"
uv run lifeos context "你好" --connector claude-code
```

### pi / Claude Code / Codex / Hermes 联动

```bash
uv run lifeos connector install pi              # 详见 docs/pi-connector.md
uv run lifeos connector install claude-code   # 详见 docs/claude-code-connector.md
uv run lifeos connector install codex            # 详见 docs/codex-connector.md
uv run lifeos connector install hermes     # 详见 docs/hermes-connector.md
uv run lifeos connector install openclaw  # 详见 docs/openclaw-connector.md
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/packs/presets/alice` | 安装 Alice 预设 |
| POST | `/packs` | 创建自定义 Agent Pack |
| POST | `/worlds` | 创建世界实例 |
| POST | `/runtime/context` | 组装 system context |
| POST | `/runtime/session/start` | 会话开始（情绪事件） |
| POST | `/runtime/session/end` | 会话结束 |

所有写接口需 Header：`X-API-Key`。

## 测试

```bash
uv run pytest
```

## 目录

- `lifeostomanyagent/server/` — FastAPI + WorldRuntimeEngine
- `lifeostomanyagent/client/` — SDK + `lifeos` CLI
- `connectors/templates/` — Claude Code / Codex hook 模板
- `connectors/hermes/` — Hermes Python Plugin
- `connectors/openclaw/` — OpenClaw TypeScript Plugin
- `connectors/pi/` — pi Extension

## 文档

- [`docs/database.md`](docs/database.md) — Postgres 表结构、JSON 字段、运行时文件布局
- [`docs/modern-agent-pack-template.md`](docs/modern-agent-pack-template.md) — 现代人物 Agent Pack 双层生成模板
- [`docs/pi-connector.md`](docs/pi-connector.md) — pi agent 安装 / 验证 / 卸载
- [`docs/codex-connector.md`](docs/codex-connector.md) — Codex 安装 / 验证 / 卸载
- [`docs/claude-code-connector.md`](docs/claude-code-connector.md) — Claude Code 安装 / 验证 / 卸载
- [`docs/openclaw-connector.md`](docs/openclaw-connector.md) — OpenClaw 安装 / 启用 / 验证 / 卸载
- [`docs/hermes-connector.md`](docs/hermes-connector.md) — Hermes 安装 / 启用 / 验证 / 卸载
- [`docs/api/lifeos-platform.md`](../docs/api/lifeos-platform.md) — 平台 API 总览
