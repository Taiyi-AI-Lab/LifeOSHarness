# LifeOS Platform 协作约定

本文件是本仓库的协作约定，适用于 LifeOS Platform 后端项目。它是自包含的，不依赖仓库外部的说明文件。

## 仓库定位

- 本仓库是 **LifeOS Platform 后端平台**：基于 Python / FastAPI 的 Agent World Runtime，外加各类 Connector 与 CLI/SDK。
- **桌面客户端（Electron 伴侣应用）的代码不在本仓库中**，它属于更大的产品愿景与 roadmap。请勿在本仓库中假设存在 Electron / 渲染进程 / IPC 代码。
- 修改前先阅读相关目录的现有实现与 `docs/` 下的说明文档，保持与现有工程风格一致。

## 技术栈与工具

- Python `>=3.11`，使用 [`uv`](https://docs.astral.sh/uv/) 管理依赖与运行。
- 安装依赖：`uv sync`；运行测试：`uv run pytest`；Lint/格式化：`uvx ruff check .` 与 `uvx ruff format .`。
- Postgres / Redis 通过 `docker-compose.yml` 提供，仅用于本地开发；测试使用 SQLite 临时库，无需外部服务。

## 目录结构约定

- `lifeostomanyagent/server/`：FastAPI 应用、引擎、API、presets、overlays。
- `lifeostomanyagent/server/runtime_state/`：persona / emotion / memory / world_engine 等运行时子系统。
- `lifeostomanyagent/client/`：Python SDK 与 `lifeos` CLI。
- `connectors/`：各 runtime（Claude Code、Codex、pi、Hermes、OpenClaw）的安装器与共享 hook 模板。
- `docs/`：架构、数据库、API 及各 connector 文档。
- `tests/`：单元与集成测试。

## 文档与需求沉淀

- 项目文档统一放在 `docs/` 下；架构、数据库、API 文档分别见 `docs/architecture.md`、`docs/database.md`、`docs/api/`。
- 当与用户讨论中明确了新的功能需求或产品决策时，应整理后写入 `docs/`（如新建 `docs/prd.md`）。未确认的内容先记录为“待确认问题”，不要当成最终需求。
- 更新文档时在原有结构上补充或修订，避免无意义覆盖。

## 安全与配置约定

- 不要把 API Key、数据库密码、访问令牌、私钥等敏感信息写入代码或提交到仓库。
- 敏感配置走环境变量或本地 `.env`（已被 `.gitignore` 忽略）；仓库中只保留 `.env.example`（占位符，无真实密钥）。
- 硬编码的 `dev-lifeos-key-change-me` 等仅为开发期 fallback，切勿用于共享或公网环境。公开部署前请遵循 `SECURITY.md` 的检查清单。
- 不要把个人机器的绝对路径（如 `/Users/<name>/...`）写入代码或文档，使用 `~/.lifeos/...` 或参数化形式。

## 修改方式

- 保持改动范围清晰、可审阅；遵循对应子目录已有的说明文档与代码风格。
- 用户可见的改动应同步更新 `CHANGELOG.md` 的 `Unreleased` 段落与相关文档。
- 不要在未被要求时执行 git 提交。
