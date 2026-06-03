from __future__ import annotations

import shutil
from pathlib import Path

PI_EXTENSION_SOURCE = Path(__file__).resolve().parents[2] / "connectors" / "pi" / "lifeos.ts"


def default_pi_extensions_dir() -> Path:
    return Path.home() / ".pi" / "agent" / "extensions"


def install_pi_extension(*, target_dir: Path | None = None, symlink: bool = False) -> Path:
    target_dir = target_dir or default_pi_extensions_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / "lifeos.ts"

    if not PI_EXTENSION_SOURCE.exists():
        raise FileNotFoundError(f"extension source missing: {PI_EXTENSION_SOURCE}")

    if destination.exists() or destination.is_symlink():
        destination.unlink()

    if symlink:
        destination.symlink_to(PI_EXTENSION_SOURCE.resolve())
    else:
        shutil.copy2(PI_EXTENSION_SOURCE, destination)

    return destination
