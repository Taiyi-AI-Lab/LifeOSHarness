from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

HERMES_PLUGIN_SOURCE = Path(__file__).resolve().parents[2] / "connectors" / "hermes"
PLUGIN_DIR_NAME = "lifeos"


def default_hermes_plugins_dir() -> Path:
    return Path.home() / ".hermes" / "plugins"


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


def install_hermes_plugin(
    *,
    plugins_dir: Path | None = None,
    symlink: bool = False,
) -> InstallResult:
    plugins_dir = plugins_dir or default_hermes_plugins_dir()
    plugins_dir.mkdir(parents=True, exist_ok=True)
    destination = plugins_dir / PLUGIN_DIR_NAME

    if not HERMES_PLUGIN_SOURCE.is_dir():
        raise FileNotFoundError(f"hermes plugin source missing: {HERMES_PLUGIN_SOURCE}")

    _remove_plugin_dir(destination)

    if symlink:
        destination.symlink_to(HERMES_PLUGIN_SOURCE.resolve())
    else:
        shutil.copytree(HERMES_PLUGIN_SOURCE, destination)

    return InstallResult(plugin_dir=destination)
