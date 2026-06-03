#!/usr/bin/env python3
"""LifeOS hook script for Claude Code / Codex (UserPromptSubmit, SessionStart, Stop, SessionEnd)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def load_config() -> dict[str, Any]:
    path = Path.home() / ".lifeos" / "config.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text("utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def api_post(config: dict[str, Any], path: str, body: dict[str, Any]) -> dict[str, Any] | None:
    server = str(config.get("server_url", "http://127.0.0.1:8000")).rstrip("/")
    api_key = str(config.get("api_key", ""))
    world_id = config.get("default_world_id")
    if not api_key or not world_id:
        return None
    payload = {**body, "world_id": world_id}
    request = urllib.request.Request(
        f"{server}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def read_event() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def emit_context(context: str) -> None:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def handle_user_prompt_submit(connector_id: str, event: dict[str, Any]) -> int:
    config = load_config()
    if not config.get("default_world_id"):
        return 0
    session_id = str(event.get("session_id") or "unknown")
    prompt = str(event.get("prompt") or "")
    api_post(
        config,
        "/runtime/turn/begin",
        {"connector_id": connector_id, "session_id": session_id},
    )
    result = api_post(
        config,
        "/runtime/context",
        {
            "connector_id": connector_id,
            "session_id": session_id,
            "user_message": prompt,
        },
    )
    if not result or not result.get("system"):
        return 0
    emit_context(str(result["system"]))
    return 0


def handle_session_start(connector_id: str, event: dict[str, Any]) -> int:
    config = load_config()
    session_id = str(event.get("session_id") or "unknown")
    api_post(
        config,
        "/runtime/session/start",
        {"connector_id": connector_id, "session_id": session_id},
    )
    return 0


def handle_stop(connector_id: str, event: dict[str, Any]) -> int:
    config = load_config()
    session_id = str(event.get("session_id") or "unknown")
    api_post(
        config,
        "/runtime/turn/finish",
        {"connector_id": connector_id, "session_id": session_id, "meaningful": True},
    )
    return 0


def handle_session_end(connector_id: str, event: dict[str, Any]) -> int:
    config = load_config()
    session_id = str(event.get("session_id") or "unknown")
    api_post(
        config,
        "/runtime/session/end",
        {"connector_id": connector_id, "session_id": session_id, "meaningful": True},
    )
    return 0


def main() -> int:
    if len(sys.argv) < 3:
        return 0
    event_name = sys.argv[1]
    connector_id = sys.argv[2]
    event = read_event()
    handlers = {
        "user-prompt-submit": handle_user_prompt_submit,
        "session-start": handle_session_start,
        "stop": handle_stop,
        "session-end": handle_session_end,
    }
    handler = handlers.get(event_name)
    if not handler:
        return 0
    return handler(connector_id, event)


if __name__ == "__main__":
    raise SystemExit(main())
