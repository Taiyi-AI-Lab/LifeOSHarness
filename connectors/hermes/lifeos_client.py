"""LifeOS API client for Hermes plugin (stdlib only)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

CONNECTOR_ID = "hermes"
DEFAULT_SERVER = "http://127.0.0.1:8000"
CONFIG_PATH = Path.home() / ".lifeos" / "config.json"


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text("utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def api_post(
    config: dict[str, Any], path: str, body: dict[str, Any]
) -> dict[str, Any] | None:
    server = str(config.get("server_url", DEFAULT_SERVER)).rstrip("/")
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
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None


def session_start(connector_id: str, session_id: str) -> None:
    config = load_config()
    if not config.get("default_world_id"):
        return
    api_post(
        config,
        "/runtime/session/start",
        {"connector_id": connector_id, "session_id": session_id},
    )


def session_end(connector_id: str, session_id: str, *, meaningful: bool = True) -> None:
    config = load_config()
    if not config.get("default_world_id"):
        return
    api_post(
        config,
        "/runtime/session/end",
        {
            "connector_id": connector_id,
            "session_id": session_id,
            "meaningful": meaningful,
        },
    )


def turn_begin(connector_id: str, session_id: str) -> None:
    config = load_config()
    if not config.get("default_world_id"):
        return
    api_post(
        config,
        "/runtime/turn/begin",
        {"connector_id": connector_id, "session_id": session_id},
    )


def turn_finish(connector_id: str, session_id: str, *, meaningful: bool = True) -> None:
    config = load_config()
    if not config.get("default_world_id"):
        return
    api_post(
        config,
        "/runtime/turn/finish",
        {
            "connector_id": connector_id,
            "session_id": session_id,
            "meaningful": meaningful,
        },
    )


def fetch_context(connector_id: str, session_id: str, user_message: str) -> str | None:
    config = load_config()
    if not config.get("default_world_id"):
        return None
    result = api_post(
        config,
        "/runtime/context",
        {
            "connector_id": connector_id,
            "session_id": session_id,
            "user_message": user_message,
        },
    )
    if not result or not result.get("injected") or not result.get("system"):
        return None
    return str(result["system"])
