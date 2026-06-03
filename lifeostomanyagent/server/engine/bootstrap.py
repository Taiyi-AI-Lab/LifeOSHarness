from __future__ import annotations

import sys
from pathlib import Path

from lifeostomanyagent.config import settings


def ensure_bws_fuxian_path() -> Path:
    root = settings.bws_fuxian_root
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root
