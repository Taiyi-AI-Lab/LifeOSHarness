from __future__ import annotations

import json
import shutil
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "connectors" / "templates"
HOOK_SCRIPT_SOURCE = TEMPLATES_DIR / "lifeos_hook.py"
LIFEOS_HOOKS_DIR = Path.home() / ".lifeos" / "hooks"
MARKER = "lifeos_hook.py"


def resolve_python() -> str:
    return sys.executable


def hook_command(event: str, connector_id: str) -> str:
    script = LIFEOS_HOOKS_DIR / "lifeos_hook.py"
    return f'"{resolve_python()}" "{script}" {event} {connector_id}'


def install_hook_script(*, symlink: bool = False) -> Path:
    LIFEOS_HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    destination = LIFEOS_HOOKS_DIR / "lifeos_hook.py"
    if not HOOK_SCRIPT_SOURCE.exists():
        raise FileNotFoundError(f"hook script missing: {HOOK_SCRIPT_SOURCE}")
    if destination.exists() or destination.is_symlink():
        destination.unlink()
    if symlink:
        destination.symlink_to(HOOK_SCRIPT_SOURCE.resolve())
    else:
        shutil.copy2(HOOK_SCRIPT_SOURCE, destination)
    destination.chmod(destination.stat().st_mode | 0o111)
    return destination


def _lifeos_hook_entry(event: str, connector_id: str, *, timeout: int = 30) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "type": "command",
        "command": hook_command(event, connector_id),
        "timeout": timeout,
    }
    if event == "user-prompt-submit":
        entry["statusMessage"] = "LifeOS context"
    return entry


def build_lifeos_hooks(connector_id: str) -> dict[str, list[dict[str, Any]]]:
    return {
        "SessionStart": [{"hooks": [_lifeos_hook_entry("session-start", connector_id)]}],
        "UserPromptSubmit": [{"hooks": [_lifeos_hook_entry("user-prompt-submit", connector_id)]}],
        "Stop": [{"hooks": [_lifeos_hook_entry("stop", connector_id, timeout=15)]}],
        "SessionEnd": [{"hooks": [_lifeos_hook_entry("session-end", connector_id, timeout=15)]}],
    }


def _is_lifeos_hook(item: dict[str, Any]) -> bool:
    command = str(item.get("command", ""))
    return MARKER in command


def _merge_hook_list(existing: list[Any], incoming: list[Any]) -> list[Any]:
    merged = deepcopy(existing)
    for group in incoming:
        hooks = group.get("hooks") if isinstance(group, dict) else None
        if not isinstance(hooks, list):
            merged.append(deepcopy(group))
            continue
        filtered = [
            g
            for g in merged
            if isinstance(g, dict)
            and not any(_is_lifeos_hook(h) for h in g.get("hooks", []) if isinstance(h, dict))
        ]
        filtered.append(deepcopy(group))
        merged = filtered
    return merged


def merge_hooks_config(existing: dict[str, Any], connector_id: str) -> dict[str, Any]:
    merged = deepcopy(existing)
    hooks = merged.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        merged["hooks"] = hooks
    for event, groups in build_lifeos_hooks(connector_id).items():
        current = hooks.get(event, [])
        if not isinstance(current, list):
            current = []
        hooks[event] = _merge_hook_list(current, groups)
    return merged


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text("utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
