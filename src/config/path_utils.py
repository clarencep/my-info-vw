"""Path resolution utilities.

Provides a single source of truth for locating project config files.
Respects the ``MY_INFO_VW_CONFIG_DIR`` environment variable so deployments
can point the entire config tree at a custom directory.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_project_root() -> Path:
    """Return the project repository root (two levels up from this file)."""
    return Path(__file__).resolve().parent.parent.parent


def get_config_root() -> Path:
    """Return the *config root* directory.

    Resolution order:

    1. ``MY_INFO_VW_CONFIG_DIR`` environment variable — if set and non-empty,
       its value is used directly.
    2. ``<PROJECT_ROOT>/config`` — the default, backward-compatible location.

    The caller is responsible for appending the specific file name, e.g.
    ``get_config_root() / "llm.yaml"``.
    """
    env_dir = os.getenv("MY_INFO_VW_CONFIG_DIR")
    if env_dir:
        return Path(env_dir)
    return get_project_root() / "config"
