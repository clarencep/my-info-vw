"""Centralized configuration path utilities for my-info-vw.

All modules that need to locate config files (llm.yaml, search.yaml, etc.)
should import from here instead of computing paths independently.
"""

from .path_utils import get_config_root, get_project_root

__all__ = ["get_config_root", "get_project_root"]
