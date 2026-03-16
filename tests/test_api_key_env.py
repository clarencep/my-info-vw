"""Tests for normalized api_key_env naming and backward compatibility."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

from dotenv import load_dotenv

load_dotenv()


class TestResolveApiKey:
    """Test LLMManager._resolve_api_key backward compatibility."""

    def test_returns_key_from_specified_env(self):
        """When api_key_env var is set, use it directly."""
        from src.llm.manager import LLMManager

        with patch.dict(os.environ, {"MY_CUSTOM_API_KEY": "sk-custom-123"}):
            key = LLMManager._resolve_api_key("MY_CUSTOM_API_KEY")
        assert key == "sk-custom-123"

    def test_falls_back_to_openai_key(self):
        """When api_key_env var is unset, falls back to OPENAI_API_KEY."""
        from src.llm.manager import LLMManager

        with patch.dict(os.environ, {
            "SOME_PROVIDER_KEY": "",
            "OPENAI_API_KEY": "sk-openai-fallback",
        }, clear=False):
            # Ensure the specific key is empty
            os.environ.pop("SOME_PROVIDER_KEY", None)
            with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-openai-fallback"}):
                key = LLMManager._resolve_api_key("SOME_PROVIDER_KEY")

        assert key == "sk-openai-fallback"

    def test_no_fallback_when_api_key_env_is_openai(self):
        """When api_key_env is literally OPENAI_API_KEY, no extra fallback."""
        from src.llm.manager import LLMManager

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-direct"}, clear=False):
            key = LLMManager._resolve_api_key("OPENAI_API_KEY")

        assert key == "sk-direct"

    def test_both_empty(self):
        """When both api_key_env and OPENAI_API_KEY are empty, return empty."""
        from src.llm.manager import LLMManager

        with patch.dict(os.environ, {
            "BIGMODEL_API_KEY": "",
            "OPENAI_API_KEY": "",
        }):
            key = LLMManager._resolve_api_key("BIGMODEL_API_KEY")

        assert key == ""

    def test_specific_key_takes_priority_over_openai(self):
        """When both are set, specific key wins."""
        from src.llm.manager import LLMManager

        with patch.dict(os.environ, {
            "BIGMODEL_API_KEY": "sk-bigmodel",
            "OPENAI_API_KEY": "sk-openai",
        }):
            key = LLMManager._resolve_api_key("BIGMODEL_API_KEY")

        assert key == "sk-bigmodel"


class TestLLMManagerWithNormalizedKeys:
    """Integration: LLMManager with provider-specific API key names."""

    def test_bigmodel_key_used_directly(self):
        """BIGMODEL_API_KEY set → loads provider successfully."""
        from src.llm.manager import LLMManager

        cfg = {
            "providers": [
                {
                    "name": "bigmodel-glm47",
                    "api_base": "https://open.bigmodel.cn/api/coding/paas/v4",
                    "api_key_env": "BIGMODEL_API_KEY",
                    "models": [{"name": "glm-4.7"}],
                }
            ],
            "fallback_order": ["bigmodel-glm47/glm-4.7"],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "llm.yaml"
            with open(yaml_path, "w") as f:
                yaml.dump(cfg, f)

            with patch.dict(os.environ, {"BIGMODEL_API_KEY": "sk-test-bigmodel"}):
                mgr = LLMManager(config_path=yaml_path)
                assert mgr._legacy_mode is False
                assert "bigmodel-glm47" in mgr._providers

    def test_fallback_to_openai_key(self):
        """BIGMODEL_API_KEY unset but OPENAI_API_KEY set → loads via fallback."""
        from src.llm.manager import LLMManager

        cfg = {
            "providers": [
                {
                    "name": "bigmodel-glm47",
                    "api_base": "https://open.bigmodel.cn/api/coding/paas/v4",
                    "api_key_env": "BIGMODEL_API_KEY",
                    "models": [{"name": "glm-4.7"}],
                }
            ],
            "fallback_order": ["bigmodel-glm47/glm-4.7"],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "llm.yaml"
            with open(yaml_path, "w") as f:
                yaml.dump(cfg, f)

            env = {"OPENAI_API_KEY": "sk-test-openai-fallback"}
            os.environ.pop("BIGMODEL_API_KEY", None)
            with patch.dict(os.environ, env, clear=False):
                mgr = LLMManager(config_path=yaml_path)
                assert mgr._legacy_mode is False
                assert "bigmodel-glm47" in mgr._providers

    def test_no_keys_skips_provider(self):
        """Neither BIGMODEL_API_KEY nor OPENAI_API_KEY → provider skipped."""
        from src.llm.manager import LLMManager

        cfg = {
            "providers": [
                {
                    "name": "bigmodel-glm47",
                    "api_base": "https://open.bigmodel.cn/api/coding/paas/v4",
                    "api_key_env": "BIGMODEL_API_KEY",
                    "models": [{"name": "glm-4.7"}],
                }
            ],
            "fallback_order": ["bigmodel-glm47/glm-4.7"],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "llm.yaml"
            with open(yaml_path, "w") as f:
                yaml.dump(cfg, f)

            os.environ.pop("BIGMODEL_API_KEY", None)
            os.environ.pop("OPENAI_API_KEY", None)
            with patch.dict(os.environ, {"BIGMODEL_API_KEY": "", "OPENAI_API_KEY": ""}):
                mgr = LLMManager(config_path=yaml_path)
                assert "bigmodel-glm47" not in mgr._providers
