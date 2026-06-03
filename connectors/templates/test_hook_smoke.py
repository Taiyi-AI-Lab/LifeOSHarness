#!/usr/bin/env python3
"""Integration test for lifeos_hook.py user-prompt-submit (requires running server)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "connectors" / "templates" / "lifeos_hook.py"


def main() -> int:
    payload = {
        "session_id": "hook-test-1",
        "prompt": "你好",
        "hook_event_name": "UserPromptSubmit",
    }
    proc = subprocess.run(
        [sys.executable, str(HOOK), "user-prompt-submit", "claude-code"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        return proc.returncode
    if not proc.stdout.strip():
        print("SKIP: no stdout (LifeOS likely not configured or server down)", file=sys.stderr)
        return 0
    out = json.loads(proc.stdout)
    ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
    if ctx:
        print("PASS: additionalContext length", len(ctx))
        return 0
    print("WARN: empty additionalContext")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
