from __future__ import annotations

from pathlib import Path

from lifeostomanyagent.connectors.pi import PI_EXTENSION_SOURCE, install_pi_extension


def test_pi_extension_source_exists():
    assert PI_EXTENSION_SOURCE.exists()
    text = PI_EXTENSION_SOURCE.read_text("utf-8")
    assert "before_agent_start" in text
    assert "/runtime/context" in text


def test_install_pi_extension_copies_file(tmp_path: Path):
    dest = install_pi_extension(target_dir=tmp_path / "extensions")
    assert dest.exists()
    assert dest.name == "lifeos.ts"
    assert "LifeOS pi Extension" in dest.read_text("utf-8")
