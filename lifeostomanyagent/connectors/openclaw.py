from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

OPENCLAW_PLUGIN_SOURCE = Path(__file__).resolve().parents[2] / "connectors" / "openclaw"
PLUGIN_DIR_NAME = "lifeos"


def default_openclaw_extensions_dir() -> Path:
    return Path.home() / ".openclaw" / "extensions"


@dataclass
class InstallResult:
    plugin_dir: Path


def _remove_plugin_dir(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def install_openclaw_plugin(
    *,
    extensions_dir: Path | None = None,
    symlink: bool = False,
) -> InstallResult:
    extensions_dir = extensions_dir or default_openclaw_extensions_dir()
    extensions_dir.mkdir(parents=True, exist_ok=True)
    destination = extensions_dir / PLUGIN_DIR_NAME

    if not OPENCLAW_PLUGIN_SOURCE.is_dir():
        raise FileNotFoundError(f"openclaw plugin source missing: {OPENCLAW_PLUGIN_SOURCE}")

    _remove_plugin_dir(destination)

    if symlink:
        destination.symlink_to(OPENCLAW_PLUGIN_SOURCE.resolve())
    else:
        shutil.copytree(OPENCLAW_PLUGIN_SOURCE, destination)

    return InstallResult(plugin_dir=destination)
