"""Tests for MY_INFO_VW_CONFIG_DIR support."""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from dotenv import load_dotenv

load_dotenv()


class TestGetConfigRoot:
    """Test get_config_root() from src.config.path_utils."""

    def test_default_uses_project_config(self):
        """Without env var, should return PROJECT_ROOT/config."""
        from src.config.path_utils import get_project_root, get_config_root

        with patch.dict(os.environ, {"MY_INFO_VW_CONFIG_DIR": ""}, clear=False):
            # Ensure env var is not set
            os.environ.pop("MY_INFO_VW_CONFIG_DIR", None)
            assert get_config_root() == get_project_root() / "config"

    def test_env_var_overrides(self):
        """When MY_INFO_VW_CONFIG_DIR is set, should return that path."""
        from src.config.path_utils import get_config_root

        with patch.dict(os.environ, {"MY_INFO_VW_CONFIG_DIR": "/etc/my-info-vw"}):
            assert get_config_root() == Path("/etc/my-info-vw")

    def test_env_var_empty_string_falls_back(self):
        """Empty string MY_INFO_VW_CONFIG_DIR should fall back to default."""
        from src.config.path_utils import get_project_root, get_config_root

        with patch.dict(os.environ, {"MY_INFO_VW_CONFIG_DIR": ""}):
            assert get_config_root() == get_project_root() / "config"


def _make_yaml_config(tmpdir: str | Path, providers=None, fallback_order=None):
    """Helper: write a test llm.yaml and return its path."""
    cfg = providers or [
        {
            "name": "test-p",
            "api_base": "https://api.test.com/v1",
            "api_key_env": "OPENAI_API_KEY",
            "models": [{"name": "test-m"}],
        }
    ]
    fallback = fallback_order or ["test-p/test-m"]
    full_cfg = {"providers": cfg, "fallback_order": fallback}
    path = Path(tmpdir) / "llm.yaml"
    with open(path, "w") as f:
        yaml.dump(full_cfg, f)
    return path


class TestLLMManagerConfigDir:
    """Test LLMManager respects MY_INFO_VW_CONFIG_DIR."""

    def test_no_env_var_existing_yaml(self):
        """Case 1: No MY_INFO_VW_CONFIG_DIR, existing config/llm.yaml → uses it."""
        from src.llm.manager import LLMManager

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            _make_yaml_config(config_dir)

            os.environ.pop("MY_INFO_VW_CONFIG_DIR", None)
            fake_path = config_dir / "llm.yaml"
            with patch("src.llm.manager.get_default_config_path", return_value=fake_path):
                mgr = LLMManager()
                assert mgr._legacy_mode is False
                assert "test-p" in mgr._providers

    def test_no_env_var_no_yaml(self):
        """Case 2: No MY_INFO_VW_CONFIG_DIR, no llm.yaml → legacy mode."""
        from src.llm.manager import LLMManager

        os.environ.pop("MY_INFO_VW_CONFIG_DIR", None)
        fake_path = Path("/nonexistent-project/config/llm.yaml")
        with patch("src.llm.manager.get_default_config_path", return_value=fake_path):
            mgr = LLMManager()
            assert mgr._legacy_mode is True

    def test_env_var_with_yaml(self):
        """Case 3: MY_INFO_VW_CONFIG_DIR set, llm.yaml exists there → uses it."""
        from src.llm.manager import LLMManager

        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = Path(tmpdir) / "custom-config"
            custom_dir.mkdir()
            custom_cfg = [
                {
                    "name": "custom-p",
                    "api_base": "https://custom.api/v1",
                    "api_key_env": "OPENAI_API_KEY",
                    "models": [{"name": "custom-m"}],
                }
            ]
            _make_yaml_config(custom_dir, providers=custom_cfg, fallback_order=["custom-p/custom-m"])

            fake_path = custom_dir / "llm.yaml"
            with patch("src.llm.manager.get_default_config_path", return_value=fake_path):
                mgr = LLMManager()
                assert mgr._legacy_mode is False
                assert "custom-p" in mgr._providers

    def test_env_var_no_yaml(self):
        """Case 4: MY_INFO_VW_CONFIG_DIR set but no llm.yaml → legacy mode."""
        from src.llm.manager import LLMManager

        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir) / "empty-config"
            empty_dir.mkdir()

            fake_path = empty_dir / "llm.yaml"
            with patch("src.llm.manager.get_default_config_path", return_value=fake_path):
                mgr = LLMManager()
                assert mgr._legacy_mode is True

    def test_explicit_config_path_takes_priority(self):
        """Explicit config_path arg should override env var."""
        from src.llm.manager import LLMManager

        cfg = {
            "providers": [
                {
                    "name": "explicit-p",
                    "api_base": "https://explicit.api/v1",
                    "api_key_env": "OPENAI_API_KEY",
                    "models": [{"name": "explicit-m"}],
                }
            ],
            "fallback_order": ["explicit-p/explicit-m"],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, dir=tmpdir) as f:
                yaml.dump(cfg, f)
                explicit_path = Path(f.name)

            irrelevant = Path("/irrelevant/path/llm.yaml")
            with patch("src.llm.manager.get_default_config_path", return_value=irrelevant):
                mgr = LLMManager(config_path=explicit_path)
                assert mgr._legacy_mode is False
                assert "explicit-p" in mgr._providers

            os.unlink(explicit_path)


class TestSearchAggregatorConfigDir:
    """Test SearchAggregator respects MY_INFO_VW_CONFIG_DIR."""

    def test_uses_env_config_dir(self):
        """When MY_INFO_VW_CONFIG_DIR points to a dir with search.yaml, should use it."""
        from src.search.aggregator import SearchAggregator

        cfg = {
            "providers": [{"name": "test-cli", "command": "echo", "enabled": True}],
            "search_order": ["test-cli"],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = Path(tmpdir) / "search-config"
            custom_dir.mkdir()
            yaml_path = custom_dir / "search.yaml"
            with open(yaml_path, "w") as f:
                yaml.dump(cfg, f)

            with patch.dict(os.environ, {"MY_INFO_VW_CONFIG_DIR": str(custom_dir)}):
                agg = SearchAggregator()
                assert agg._use_provider_manager is True
