from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lifeostomanyagent.connectors.hooks_base import (
    install_hook_script,
    load_json,
    merge_hooks_config,
    save_json,
)


@dataclass
class InstallResult:
    settings_path: Path
    hook_script: Path


def default_claude_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def install_claude_code_hooks(
    *,
    settings_path: Path | None = None,
    symlink: bool = False,
) -> InstallResult:
    settings_path = settings_path or default_claude_settings_path()
    hook_script = install_hook_script(symlink=symlink)
    existing = load_json(settings_path)
    merged = merge_hooks_config(existing, "claude-code")
    save_json(settings_path, merged)
    return InstallResult(settings_path=settings_path, hook_script=hook_script)
