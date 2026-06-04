# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning once versioned releases begin.

## Unreleased

### Added

- Added SQLite-first unified SQL storage for core runtime state, with optional PostgreSQL via `DATABASE_URL` and automatic import of legacy runtime files.
- Added an intent gate for `/runtime/context`: LifeOS context is injected only for clear chitchat / companionship turns by default.
- Added optional DeepSeek-based intent classification via `LIFEOS_INTENT_CLASSIFIER=llm`, with deterministic rule fallback.
- Added community and contribution files: `AGENTS.md`, `CONTRIBUTING.md`, and `CODE_OF_CONDUCT.md`.
- Added backend-only repository scope notes and a security deployment checklist.

### Changed

- Changed Docker Compose to start the API with SQLite by default; PostgreSQL and Redis are now optional profiles.
- Updated connectors to start and finish LifeOS turns only when context was actually injected.
- Replaced machine-specific paths and removed dead Electron IPC metadata from backend world debug specs.

## 0.1.0 - 2026-06-03

### Added

- Initial public release of LifeOS Platform, a local-first, self-hosted Agent World Runtime backend (Python/FastAPI).
- Agent World Runtime with persistent persona, memory, emotion, world facts, and dreams state per World instance.
- Structured Agent Packs with the built-in Alice example preset.
- FastAPI Runtime API for packs, worlds, context assembly, sessions, and dreams, protected by `X-API-Key`.
- Prompt Composer with connector-aware budgets, overlays, and trim priorities.
- Connectors for Claude Code, Codex, pi, Hermes, and OpenClaw, plus shared hook templates.
- Python SDK and `lifeos` CLI.
- DeepSeek-backed dream generation with local rule-based fallback.
- Docker Compose stack for local Postgres, Redis, and API development.
- Project documentation under `docs/`.
