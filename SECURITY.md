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
