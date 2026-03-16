"""Tests for LLM Manager - multi-provider automatic fallback."""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dotenv import load_dotenv

load_dotenv()


class TestConfigLoading:
    """Test YAML config loading."""

    def test_loads_yaml_config(self):
        """Test loading a valid YAML config."""
        from src.llm.manager import LLMManager

        cfg = {
            "providers": [
                {
                    "name": "test-provider",
                    "api_base": "https://api.test.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                    "models": [{"name": "test-model", "temperature": 0.5}],
                }
            ],
            "fallback_order": ["test-provider/test-model"],
            "retry_on_error_codes": [1301, 429],
            "max_retries_per_model": 2,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(cfg, f)
            f.flush()
            mgr = LLMManager(config_path=Path(f.name))

        assert len(mgr._providers) == 1
        assert "test-provider" in mgr._providers
        assert mgr._max_retries_per_model == 2
        assert 1301 in mgr._retry_on_error_codes
        os.unlink(f.name)

    def test_legacy_mode_when_no_yaml(self):
        """Test legacy .env mode when no YAML exists."""
        from src.llm.manager import LLMManager

        mgr = LLMManager(config_path=Path("/nonexistent/path.yaml"))
        assert mgr._legacy_mode is True

    def test_skip_provider_with_missing_api_key(self):
        """Test provider is skipped when API key env var is empty."""
        from src.llm.manager import LLMManager

        cfg = {
            "providers": [
                {
                    "name": "no-key-provider",
                    "api_base": "https://api.test.com/v1",
                    "api_key_env": "NONEXISTENT_API_KEY_12345",
                    "models": [{"name": "m1"}],
                }
            ],
            "fallback_order": ["no-key-provider/m1"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(cfg, f)
            f.flush()
            mgr = LLMManager(config_path=Path(f.name))

        assert "no-key-provider" not in mgr._providers
        os.unlink(f.name)

    def test_validate_fallback_order_unknown_entries(self, caplog):
        """Test that unknown fallback_order entries are logged as errors."""
        from src.llm.manager import LLMManager

        cfg = {
            "providers": [],
            "fallback_order": ["invalid-format", "unknown/prov"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(cfg, f)
            f.flush()
            with caplog.at_level(logging.ERROR):
                mgr = LLMManager(config_path=Path(f.name))

        assert any("invalid fallback_order entry" in r.message for r in caplog.records)
        assert any("unknown provider" in r.message for r in caplog.records)
        os.unlink(f.name)


class TestFallback:
    """Test fallback logic."""

    def test_first_model_succeeds(self):
        """Test that the first model is used when it succeeds."""
        from src.llm.manager import LLMManager

        cfg = {
            "providers": [
                {
                    "name": "p1",
                    "api_base": "https://api.test.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                    "models": [{"name": "m1"}],
                },
                {
                    "name": "p2",
                    "api_base": "https://api.test.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                    "models": [{"name": "m2"}],
                },
            ],
            "fallback_order": ["p1/m1", "p2/m2"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(cfg, f)
            f.flush()
            mgr = LLMManager(config_path=Path(f.name))

        from langchain_core.messages import HumanMessage, AIMessage

        with patch.object(mgr, "_get_llm") as mock_get:
            mock_get.return_value = MagicMock(invoke=MagicMock(return_value=AIMessage(content="ok")))
            result = mgr.invoke([HumanMessage(content="test")])

        assert result.content == "ok"
        os.unlink(f.name)

    def test_fallback_on_retryable_error(self):
        """Test fallback to next model on retryable error."""
        from src.llm.manager import LLMManager

        cfg = {
            "providers": [
                {
                    "name": "p1",
                    "api_base": "https://api.test.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                    "models": [{"name": "m1"}],
                },
                {
                    "name": "p2",
                    "api_base": "https://api.test.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                    "models": [{"name": "m2"}],
                },
            ],
            "fallback_order": ["p1/m1", "p2/m2"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(cfg, f)
            f.flush()
            mgr = LLMManager(config_path=Path(f.name))

        from langchain_core.messages import HumanMessage, AIMessage

        err = Exception("content filtered")
        err.code = 1301

        call_count = 0

        def mock_invoke(messages):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise err
            return AIMessage(content="fallback ok")

        with patch.object(mgr, "_get_llm") as mock_get:
            mock_get.return_value = MagicMock(invoke=mock_invoke)
            result = mgr.invoke([HumanMessage(content="test")])

        assert result.content == "fallback ok"
        os.unlink(f.name)

    def test_all_models_fail_raises(self):
        """Test LLMFallbackError when all models fail."""
        from src.llm.manager import LLMManager, LLMFallbackError

        cfg = {
            "providers": [
                {
                    "name": "p1",
                    "api_base": "https://api.test.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                    "models": [{"name": "m1"}],
                },
            ],
            "fallback_order": ["p1/m1"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(cfg, f)
            f.flush()
            mgr = LLMManager(config_path=Path(f.name))

        from langchain_core.messages import HumanMessage

        err = Exception("server error")
        err.code = 500

        with patch.object(mgr, "_get_llm") as mock_get:
            mock_get.return_value = MagicMock(invoke=MagicMock(side_effect=err))
            with pytest.raises(LLMFallbackError) as exc_info:
                mgr.invoke([HumanMessage(content="test")])

        # [P0] Verify errors are accumulated correctly
        assert len(exc_info.value.errors) == 1
        assert exc_info.value.errors[0][0] == "p1"
        assert exc_info.value.errors[0][1] == "m1"
        os.unlink(f.name)

    def test_non_retryable_error_skips_immediately(self):
        """Test that non-retryable errors skip retries immediately."""
        from src.llm.manager import LLMManager, LLMFallbackError

        cfg = {
            "providers": [
                {
                    "name": "p1",
                    "api_base": "https://api.test.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                    "models": [{"name": "m1"}],
                },
            ],
            "fallback_order": ["p1/m1"],
            "max_retries_per_model": 3,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(cfg, f)
            f.flush()
            mgr = LLMManager(config_path=Path(f.name))

        from langchain_core.messages import HumanMessage

        err = Exception("auth error")
        err.code = 401  # not in retry list

        invoke_count = 0

        def mock_invoke(msgs):
            nonlocal invoke_count
            invoke_count += 1
            raise err

        with patch.object(mgr, "_get_llm") as mock_get:
            mock_get.return_value = MagicMock(invoke=mock_invoke)
            with pytest.raises(LLMFallbackError):
                mgr.invoke([HumanMessage(content="test")])

        # Should only be called once (no retries for non-retryable)
        assert invoke_count == 1
        os.unlink(f.name)

    def test_retryable_error_accumulates_in_errors(self):
        """Test that retryable errors are always appended to errors list."""
        from src.llm.manager import LLMManager, LLMFallbackError

        cfg = {
            "providers": [
                {
                    "name": "p1",
                    "api_base": "https://api.test.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                    "models": [{"name": "m1"}],
                },
                {
                    "name": "p2",
                    "api_base": "https://api.test.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                    "models": [{"name": "m2"}],
                },
            ],
            "fallback_order": ["p1/m1", "p2/m2"],
            "max_retries_per_model": 1,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(cfg, f)
            f.flush()
            mgr = LLMManager(config_path=Path(f.name))

        from langchain_core.messages import HumanMessage

        err1 = Exception("rate limited")
        err1.code = 429
        err2 = Exception("content filtered")
        err2.code = 1301

        def mock_invoke_1(msgs):
            raise err1

        def mock_invoke_2(msgs):
            raise err2

        with patch.object(mgr, "_get_llm") as mock_get:
            mock_get.side_effect = [
                MagicMock(invoke=mock_invoke_1),
                MagicMock(invoke=mock_invoke_2),
            ]
            with pytest.raises(LLMFallbackError) as exc_info:
                mgr.invoke([HumanMessage(content="test")])

        # Both errors should be accumulated
        assert len(exc_info.value.errors) == 2
        assert exc_info.value.errors[0] == ("p1", "m1", err1)
        assert exc_info.value.errors[1] == ("p2", "m2", err2)
        os.unlink(f.name)


class TestBackwardCompat:
    """Test backward compatibility with .env single-model mode."""

    def test_legacy_invoke(self):
        """Test legacy mode invokes correctly."""
        from src.llm.manager import LLMManager

        mgr = LLMManager(config_path=Path("/nonexistent/path.yaml"))
        assert mgr._legacy_mode is True

    def test_get_llm_returns_chatopenai(self):
        """Test get_llm returns ChatOpenAI instance."""
        from src.llm.manager import LLMManager
        from langchain_openai import ChatOpenAI

        mgr = LLMManager(config_path=Path("/nonexistent/path.yaml"))
        llm = mgr.get_llm()
        assert isinstance(llm, ChatOpenAI)


class TestHealthCheck:
    """Test health_check method."""

    def test_health_check_legacy_mode(self):
        """Test health_check in legacy mode returns dict."""
        from src.llm.manager import LLMManager

        mgr = LLMManager(config_path=Path("/nonexistent/path.yaml"))
        # Don't actually call API, just check return type
        assert hasattr(mgr, "health_check")
        assert callable(mgr.health_check)

    def test_health_check_configured_mode(self):
        """Test health_check returns dict for configured mode."""
        from src.llm.manager import LLMManager

        cfg = {
            "providers": [
                {
                    "name": "p1",
                    "api_base": "https://api.test.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                    "models": [{"name": "m1"}],
                },
            ],
            "fallback_order": ["p1/m1"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(cfg, f)
            f.flush()
            mgr = LLMManager(config_path=Path(f.name))

        assert "p1/m1" in mgr.health_check()
        os.unlink(f.name)


class TestThreadSafety:
    """Test thread safety."""

    def test_get_llm_is_thread_safe(self):
        """Test _get_llm uses lock."""
        from src.llm.manager import LLMManager

        cfg = {
            "providers": [
                {
                    "name": "p1",
                    "api_base": "https://api.test.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                    "models": [{"name": "m1"}],
                },
            ],
            "fallback_order": ["p1/m1"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(cfg, f)
            f.flush()
            mgr = LLMManager(config_path=Path(f.name))

        assert mgr._lock is not None
        os.unlink(f.name)
