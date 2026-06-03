from __future__ import annotations

import os
import re
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
    hooks_path: Path
    config_path: Path
    hook_script: Path


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def _ensure_codex_hooks_enabled(config_path: Path) -> None:
    if config_path.exists():
        text = config_path.read_text("utf-8")
    else:
        text = ""
    if re.search(r"^\s*hooks\s*=\s*true\s*$", text, re.MULTILINE):
        return
    if "[features]" in text:
        if not re.search(r"^\s*hooks\s*=", text, re.MULTILINE):
            text = re.sub(
                r"(\[features\][^\[]*)",
                r"\1hooks = true\n",
                text,
                count=1,
                flags=re.DOTALL,
            )
    else:
        suffix = "\n" if text and not text.endswith("\n") else ""
        text = f"{text}{suffix}[features]\nhooks = true\n"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(text, "utf-8")


def install_codex_hooks(
    *,
    codex_home: Path | None = None,
    symlink: bool = False,
) -> InstallResult:
    home = codex_home or default_codex_home()
    hooks_path = home / "hooks.json"
    config_path = home / "config.toml"
    hook_script = install_hook_script(symlink=symlink)
    existing = load_json(hooks_path)
    merged = merge_hooks_config(existing, "codex")
    save_json(hooks_path, merged)
    _ensure_codex_hooks_enabled(config_path)
    return InstallResult(hooks_path=hooks_path, config_path=config_path, hook_script=hook_script)
