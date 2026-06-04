# LifeOS Web Console

This directory contains the frontend code for the LifeOS Web Console.

The console will make the Agent World Runtime visible and easier to operate:

- Browse Worlds and Agent Packs.
- Inspect persona, emotion, memory, dreams, and world facts.
- Test connector context injection.
- Review `/runtime/context` traces, intent decisions, block order, and injected system previews.
- Support future Agent Pack creation and editing flows.

The first implementation should stay focused on a developer/operator console rather than a marketing site. Keep UI work consistent with the root project scope: this repository hosts the LifeOS Platform backend, connectors, CLI/SDK, and the future web console.

## Initial MVP

1. Overview
2. Worlds
3. World detail
4. Agent Packs
5. Runtime Inspector

Memory, dreams, world facts, and connector traces start as tabs inside World detail before they become standalone pages.

## Development

Start the FastAPI backend from the repository root:

```bash
uv run uvicorn lifeostomanyagent.server.main:app --reload --port 8000
```

Then start the console:

```bash
cd web
npm install
npm run dev
```

The Vite dev server runs on `http://127.0.0.1:5173` and proxies `/api/*` to the FastAPI server at `http://127.0.0.1:8000`.

The console uses the same `X-API-Key` model as the backend. In local development, the default API key is:

```text
dev-lifeos-key-change-me
```

## Checks

```bash
npm run test
npm run typecheck
npm run build
```
