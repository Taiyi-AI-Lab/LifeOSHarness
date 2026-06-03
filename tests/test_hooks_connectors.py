from __future__ import annotations

import json
from pathlib import Path

import pytest

from lifeostomanyagent.connectors.claude_code import install_claude_code_hooks
from lifeostomanyagent.connectors.codex import install_codex_hooks
from lifeostomanyagent.connectors.hooks_base import (
    HOOK_SCRIPT_SOURCE,
    build_lifeos_hooks,
    hook_command,
    merge_hooks_config,
)


def test_build_lifeos_hooks_has_required_events():
    hooks = build_lifeos_hooks("claude-code")
    assert "UserPromptSubmit" in hooks
    assert "SessionStart" in hooks
    assert "Stop" in hooks
    assert "SessionEnd" in hooks
    command = hooks["UserPromptSubmit"][0]["hooks"][0]["command"]
    assert "lifeos_hook.py" in command
    assert "user-prompt-submit" in command
    assert "claude-code" in command


def test_merge_hooks_config_replaces_existing_lifeos_hooks():
    existing = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": 'python3 ~/.lifeos/hooks/lifeos_hook.py user-prompt-submit old',
                        }
                    ]
                }
            ],
            "Stop": [{"hooks": [{"type": "command", "command": "echo keep"}]}],
        }
    }
    merged = merge_hooks_config(existing, "codex")
    submit_cmds = [h["command"] for h in merged["hooks"]["UserPromptSubmit"][0]["hooks"]]
    assert len(submit_cmds) == 1
    assert "codex" in submit_cmds[0]
    stop_cmds = [
        h["command"]
        for group in merged["hooks"]["Stop"]
        for h in group["hooks"]
    ]
    assert any("echo keep" in cmd for cmd in stop_cmds)
    assert any("lifeos_hook.py" in cmd and "codex" in cmd for cmd in stop_cmds)


def test_install_claude_code_hooks(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "lifeostomanyagent.connectors.hooks_base.LIFEOS_HOOKS_DIR",
        tmp_path / "hooks",
    )
    settings = tmp_path / "settings.json"
    result = install_claude_code_hooks(settings_path=settings, symlink=False)
    assert result.hook_script.exists()
    data = json.loads(settings.read_text("utf-8"))
    assert "UserPromptSubmit" in data["hooks"]
    assert HOOK_SCRIPT_SOURCE.read_text("utf-8")[:40] in result.hook_script.read_text("utf-8")


def test_install_codex_hooks(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "lifeostomanyagent.connectors.hooks_base.LIFEOS_HOOKS_DIR",
        tmp_path / "hooks",
    )
    codex_home = tmp_path / "codex"
    result = install_codex_hooks(codex_home=codex_home, symlink=False)
    hooks = json.loads(result.hooks_path.read_text("utf-8"))
    assert hooks["hooks"]["UserPromptSubmit"]
    assert "hooks = true" in result.config_path.read_text("utf-8")


def test_hook_command_uses_current_python():
    cmd = hook_command("user-prompt-submit", "claude-code")
    assert "user-prompt-submit" in cmd
    assert "claude-code" in cmd
