# Contributing to LifeOS Platform

Thanks for your interest in contributing! LifeOS Platform is the local-first, self-hosted Agent World Runtime backend (Python/FastAPI). This guide explains how to set up your environment, run tests, and propose changes.

## Code of Conduct

By participating in this project you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Prerequisites

- Python `>=3.11`
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- Docker (optional, for Postgres/Redis via `docker-compose.yml`)

## Getting Started

```bash
git clone <your-fork-url>
cd lifeostomanyagent
cp .env.example .env          # development defaults; change secrets before real use
uv sync                       # install dependencies into .venv
```

The test suite uses an in-memory/SQLite database and does not require Postgres or Redis, so you can run it immediately after `uv sync`.

## Branch Strategy

- `main` is the integration branch and should always be green.
- Create a feature branch from `main` for each change: `feat/<short-name>`, `fix/<short-name>`, `docs/<short-name>`, or `chore/<short-name>`.
- Keep changes focused and reviewable. Open a pull request against `main` and describe the motivation and approach.
- Rebase or merge `main` into your branch to resolve conflicts before requesting review.

## Running Tests

Run the full suite with:

```bash
uv run pytest
```

Run a single file or test:

```bash
uv run pytest tests/test_runtime.py
uv run pytest tests/test_api.py -k context
```

All pull requests must keep the test suite passing.

## Connector Tests

Connectors live under `connectors/` (Hermes, OpenClaw, pi, and shared templates) with matching Python tests under `tests/`:

- `tests/test_hooks_connectors.py`, `tests/test_hermes_connector.py`, `tests/test_openclaw_connector.py`, `tests/test_pi_connector.py` exercise connector context-building logic and run as part of `uv run pytest`.
- `connectors/templates/test_hook_smoke.py` is an **integration** smoke test that shells out to `lifeos_hook.py` and expects a running LifeOS server. It is safe to run without a server — it prints `SKIP` / `WARN` and exits `0` when LifeOS is not configured or unreachable. Run it manually:

  ```bash
  uv run python connectors/templates/test_hook_smoke.py
  ```

When adding a new connector, include unit tests that cover its context shaping (budget, overlay, trim priority) so it runs in CI without external dependencies.

## Linting and Formatting

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting. Configuration lives in `pyproject.toml`.

```bash
uvx ruff check .       # lint
uvx ruff format .      # auto-format
```

Please run both before opening a pull request. CI runs `ruff check` and the test suite on every push and pull request.

## Commit and PR Guidelines

- Write clear commit messages (a short imperative summary line; add a body when useful).
- Update relevant docs under `docs/` and the `CHANGELOG.md` `Unreleased` section when your change is user-facing.
- Do not commit secrets. `.env`, `data/`, local databases, and logs are git-ignored on purpose; only `.env.example` (with blank secrets) is tracked.

## Reporting Security Issues

Please do not open public issues for security vulnerabilities. Follow the process in [SECURITY.md](SECURITY.md).
