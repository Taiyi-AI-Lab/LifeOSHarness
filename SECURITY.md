# Security Policy

LifeOS Platform is local-first software. The default configuration is intended for development on a trusted machine, not for public internet exposure.

## Supported Versions

Security fixes target the `main` branch until the project starts publishing versioned releases.

## Deployment Guidance

- Change `LIFEOS_API_KEY` before running outside local development. The sample key `dev-lifeos-key-change-me` is not safe for shared networks.
- Bind the API to localhost or a trusted private network unless you have added your own authentication, TLS, rate limiting, and access controls.
- Treat `LIFEOS_DATA_ROOT` as sensitive. It stores world runtime state, user memory, dreams, and SQLite world facts.
- Keep `.env`, local databases, runtime data, logs, and connector config files out of git.
- Do not commit third-party API keys such as `DEEPSEEK_API_KEY`.
- Connector installers may modify files under user home directories such as `~/.lifeos`, `~/.claude`, `~/.codex`, `~/.hermes`, `~/.openclaw`, or `~/.pi`. Review connector docs before installation.

## Pre-Release / Deployment Checklist

Before exposing LifeOS beyond your local development machine, confirm every item below:

- [ ] **Rotate `LIFEOS_API_KEY`.** The default `dev-lifeos-key-change-me` is a development-only fallback (see `lifeostomanyagent/config.py`). Replace it with a long, random secret supplied via environment or your secret manager.
- [ ] **Do not bind `0.0.0.0` on a public host.** The default `LIFEOS_HOST=0.0.0.0` is meant for local/dev or containers behind a private network. For anything internet-facing, bind to `127.0.0.1` and front it with a trusted reverse proxy (TLS, authentication, rate limiting), or restrict it to a private network boundary.
- [ ] **Change the Compose database/cache defaults.** `docker-compose.yml` ships `POSTGRES_USER=lifeos` / `POSTGRES_PASSWORD=lifeos` and an unauthenticated Redis purely for local development. Set strong credentials and never reuse these defaults in shared or production environments.
- [ ] **Keep secrets out of git.** Verify `.env`, `data/`, local databases, logs, and connector config files are ignored (they are covered by `.gitignore`). Only `.env.example`, which contains no real secrets, should be committed.
- [ ] **Never commit third-party API keys.** Provide `DEEPSEEK_API_KEY` and similar values through the environment, not source control. `.env.example` intentionally leaves them blank.
- [ ] **Protect `LIFEOS_DATA_ROOT`.** It stores world runtime state, user memory, dreams, and SQLite world facts. Back it up and restrict filesystem permissions.
- [ ] **Review connector installers.** They may modify files under user home directories such as `~/.lifeos`, `~/.claude`, `~/.codex`, `~/.hermes`, `~/.openclaw`, or `~/.pi`. Read each connector doc before installing.

## Current Security Model

- API authentication uses a single shared `X-API-Key`.
- There is no multi-user permission model.
- There is no built-in TLS termination.
- Runtime state is stored on local disk and protected by host filesystem permissions.

For production-like deployments, place LifeOS behind a trusted reverse proxy or private network boundary and manage secrets through your deployment platform.

## Reporting a Vulnerability

If GitHub security advisories are enabled for the repository, please report vulnerabilities through a private security advisory. Otherwise, open an issue with a minimal description and avoid posting secrets, tokens, private logs, or full runtime state dumps.

Please include:

- Affected commit or version.
- Steps to reproduce.
- Impact and affected data.
- Suggested mitigation, if known.
