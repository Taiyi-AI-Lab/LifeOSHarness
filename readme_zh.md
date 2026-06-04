# LifeOS Platform

English version: [README.md](README.md)

> **仓库定位：** 本仓库是 **LifeOS Platform 后端平台** —— 一个基于 Python/FastAPI 的 Agent World Runtime，外加各类 Connector 与 CLI/SDK。**Alice 桌面客户端**（Electron 伴侣应用）属于更大的产品愿景与 roadmap，其代码**不包含**在本仓库中。本仓库的所有内容都作为无界面、自托管的后端服务运行。

LifeOS Platform 是一个 local-first、自托管的 Agent World Runtime，用来构建更有温度、更有连续性的 Agent。它给 Agent 一个持久身份、记忆、情绪状态、生活背景、梦境和可跨多个 Agent 客户端共享的世界。

LifeOS 的目标是让 Agent 更有温度。温度不是多说几句亲切话，而是它能记得关系、承接情绪、理解生活背景、保留共同经历，并且在不同工具里仍然像同一个持续存在的伙伴。Claude Code、Codex、pi、Hermes、OpenClaw 等不同运行时都可以通过 Connector 拉取同一个 World 的上下文。

Alice 是仓库自带的 example preset，用来展示结构化 Agent Pack 的能力；你可以通过 `POST /packs` 创建自己的 Pack。

## 创新点

- **Agent World Runtime**：把人格、记忆、情绪、世界事实和梦境做成一个持续存在的 World，而不是散落在某个客户端会话里。
- **结构化 Agent Pack**：用 `identity`、`behavior_profile`、`behavior_trajectory`、`world_rules` 描述一个 Agent，让人物设定可以被审阅、复用和演化。
- **有温度的 Runtime State**：persona 记录关系与近况，emotion 记录情绪状态，memory 保存用户偏好与共同经历，world facts 保存生活世界，dreams 把昨日互动整理成象征性上下文。
- **多客户端一致性**：同一个 World 可以被 Claude Code、Codex、pi、Hermes、OpenClaw 等客户端共享，Agent 不会因为换工具就失去连续性。
- **Connector-aware Context**：根据不同 agent runtime 的能力、预算和 hook 形态组装上下文，让“有温度”能实际注入到工作流里。

```mermaid
flowchart TD
    Client["Agent client<br/>Claude Code / Codex / pi / Hermes / OpenClaw"] --> Connector["Connector hook or plugin"]
    Connector --> API["FastAPI Runtime API"]
    API --> Service["LifeOSService"]
    Service --> DB["Postgres<br/>packs / worlds / sessions"]
    Service --> Engine["WorldRuntimeEngine"]
    Engine --> State["runtime_state<br/>persona / emotion / memory / world facts / dreams"]
    Engine --> Composer["PromptComposer"]
    Composer --> Profile["ConnectorProfile<br/>budget / overlay / trim priority"]
    Composer --> Connector
```

## 核心概念

- **Agent Pack**：结构化人物模板，包含身份、行为画像、行为轨迹、世界规则和启用的 runtime 模块。
- **World Instance**：基于 Pack 创建的独立世界，每个 world 有自己的 persona、emotion、memory、world facts 和 dreams 状态。
- **Runtime State**：仓库内嵌的状态子系统，负责读写本地文件和 SQLite，不依赖外部私有目录。
- **Prompt Composer**：按 connector、预算和优先级组装 system context。
- **Connector**：把 LifeOS context 注入到 Claude Code、Codex、pi、Hermes、OpenClaw 等 agent runtime。

## 5 分钟 Quickstart

### 1. 启动依赖

```bash
cp .env.example .env
docker compose up -d postgres redis
```

`.env.example` 使用开发默认值。公开部署或联网使用前，请修改 `LIFEOS_API_KEY`，详见 [SECURITY.md](SECURITY.md)。

### 2. 安装依赖并启动 API

```bash
uv sync
uv run uvicorn lifeostomanyagent.server.main:app --reload --port 8000
```

也可以直接构建 API 镜像：

```bash
docker compose build api
docker compose up -d api
```

### 3. 创建示例 World 并拉取 context

```bash
uv run lifeos login --server http://127.0.0.1:8000 --api-key dev-lifeos-key-change-me
uv run lifeos world-create --pack alice --name "我的 Alice"
uv run lifeos context "你好" --connector claude-code
```

### 4. 可选：启用梦境模块的 LLM 生成

未配置 DeepSeek 时，dreams 会自动回退到本地规则生成。

```bash
DEEPSEEK_API_KEY=<your DeepSeek API key>
DEEPSEEK_DREAM_MODEL=deepseek-v4-pro
DEEPSEEK_DREAM_BASE_URL=https://api.deepseek.com
```

### 5. 可选：安装 Connector

```bash
uv run lifeos connector install pi            # docs/pi-connector.md
uv run lifeos connector install claude-code   # docs/claude-code-connector.md
uv run lifeos connector install codex         # docs/codex-connector.md
uv run lifeos connector install hermes        # docs/hermes-connector.md
uv run lifeos connector install openclaw      # docs/openclaw-connector.md
```

Connector installer 会修改对应 agent 客户端的本地配置文件。安装、验证和卸载步骤见各 connector 文档。

## API 概览

所有写接口需 Header：`X-API-Key`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/packs/presets/alice` | 安装/刷新 Alice 示例 preset |
| POST | `/packs` | 创建自定义 Agent Pack |
| GET | `/packs` | 列出 Agent Pack |
| POST | `/worlds` | 创建 World Instance |
| GET | `/worlds` | 列出 World Instance |
| POST | `/runtime/context` | 组装 connector-aware system context |
| POST | `/runtime/session/start` | 会话开始事件 |
| POST | `/runtime/session/end` | 会话结束事件 |
| POST | `/runtime/dreams/run` | 手动生成梦境 |

完整接口说明见 [docs/api/lifeos-platform.md](docs/api/lifeos-platform.md)。

## 目录

- `lifeostomanyagent/server/`：FastAPI API、WorldRuntimeEngine、PromptComposer。
- `lifeostomanyagent/server/runtime_state/`：内嵌 persona / emotion / memory / world facts 状态子系统。
- `lifeostomanyagent/client/`：Python SDK 与 `lifeos` CLI。
- `connectors/templates/`：Claude Code / Codex hook 模板。
- `connectors/hermes/`：Hermes Python Plugin。
- `connectors/openclaw/`：OpenClaw TypeScript Plugin。
- `connectors/pi/`：pi Extension。
- `docs/`：架构、数据库、API 和 connector 文档。

## 测试

```bash
uv run pytest
```

## 文档

- [docs/architecture.md](docs/architecture.md)：架构、数据流和设计边界。
- [docs/database.md](docs/database.md)：Postgres 表结构、JSON 字段、运行时文件布局。
- [docs/api/lifeos-platform.md](docs/api/lifeos-platform.md)：平台 API 总览。
- [docs/modern-agent-pack-template.md](docs/modern-agent-pack-template.md)：现代人物 Agent Pack 双层生成模板。
- [docs/pi-connector.md](docs/pi-connector.md)：pi agent 安装 / 验证 / 卸载。
- [docs/codex-connector.md](docs/codex-connector.md)：Codex 安装 / 验证 / 卸载。
- [docs/claude-code-connector.md](docs/claude-code-connector.md)：Claude Code 安装 / 验证 / 卸载。
- [docs/openclaw-connector.md](docs/openclaw-connector.md)：OpenClaw 安装 / 启用 / 验证 / 卸载。
- [docs/hermes-connector.md](docs/hermes-connector.md)：Hermes 安装 / 启用 / 验证 / 卸载。

## 安全

默认配置面向本地开发。公开部署前请阅读 [SECURITY.md](SECURITY.md)，至少修改 `LIFEOS_API_KEY`，并只把服务暴露给可信网络。SECURITY.md 中提供了一份**发布/部署前检查清单**（轮换 API Key、不要对公网暴露 `0.0.0.0`、修改 Compose 中 Postgres/Redis 的开发默认密码、把密钥排除在 git 之外）。硬编码的 `dev-lifeos-key-change-me` 仅作为开发期 fallback —— 切勿在共享或公网环境中使用。

## License

MIT License. See [LICENSE](LICENSE).
