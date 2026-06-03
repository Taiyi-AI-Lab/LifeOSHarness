from __future__ import annotations

import json
from pathlib import Path

from lifeostomanyagent.connectors.openclaw import (
    OPENCLAW_PLUGIN_SOURCE,
    install_openclaw_plugin,
)


def test_openclaw_plugin_source_has_required_files():
    assert (OPENCLAW_PLUGIN_SOURCE / "openclaw.plugin.json").exists()
    assert (OPENCLAW_PLUGIN_SOURCE / "index.ts").exists()
    assert (OPENCLAW_PLUGIN_SOURCE / "lifeos-client.ts").exists()
    manifest = json.loads((OPENCLAW_PLUGIN_SOURCE / "openclaw.plugin.json").read_text("utf-8"))
    assert manifest["id"] == "lifeos"
    index = (OPENCLAW_PLUGIN_SOURCE / "index.ts").read_text("utf-8")
    assert "before_prompt_build" in index
    assert "session_start" in index
    assert "agent_end" in index
    assert "session_end" in index
    assert 'CONNECTOR_ID = "openclaw"' in (OPENCLAW_PLUGIN_SOURCE / "lifeos-client.ts").read_text("utf-8")


def test_install_openclaw_plugin_copies_files(tmp_path: Path):
    ext_dir = tmp_path / "extensions"
    result = install_openclaw_plugin(extensions_dir=ext_dir, symlink=False)
    assert result.plugin_dir == ext_dir / "lifeos"
    assert (result.plugin_dir / "openclaw.plugin.json").exists()
    assert (result.plugin_dir / "index.ts").exists()
    assert (result.plugin_dir / "lifeos-client.ts").exists()
    assert (result.plugin_dir / "package.json").exists()


def test_install_openclaw_plugin_symlink(tmp_path: Path):
    ext_dir = tmp_path / "extensions"
    result = install_openclaw_plugin(extensions_dir=ext_dir, symlink=True)
    assert result.plugin_dir.is_symlink()
    assert result.plugin_dir.resolve() == OPENCLAW_PLUGIN_SOURCE.resolve()
