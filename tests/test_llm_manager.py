"""Tests for LLMManager - config loading, fallback logic, backward compatibility."""

import os
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_yaml_config(path: Path, extra: str = "") -> None:
    """Write a minimal llm.yaml for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "providers:\n"
        "  - name: prov-a\n"
        "    api_base: https://api-a.example.com/v4\n"
        "    api_key_env: OPENAI_API_KEY\n"
        "    models:\n"
        "      - name: model-1\n"
        "        temperature: 0.5\n"
        "  - name: prov-b\n"
        "    api_base: https://api-b.example.com/v4\n"
        "    api_key_env: OPENAI_API_KEY\n"
        "    models:\n"
        "      - name: model-2\n"
        "        temperature: 0.8\n"
        + extra,
        encoding="utf-8",
    )


def _messages():
    return [SystemMessage(content="test"), HumanMessage(content="hello")]


# ---------------------------------------------------------------------------
# 1. Config loading
# ---------------------------------------------------------------------------

class TestConfigLoading:
    def test_loads_yaml_config(self, tmp_path, monkeypatch):
        """YAML config is parsed into provider dict and fallback order."""
        cfg = tmp_path / "llm.yaml"
        _make_yaml_config(
            cfg,
            "fallback_order:\n"
            "  - prov-a/model-1\n"
            "  - prov-b/model-2\n"
            "retry_on_error_codes: [1301, 500]\n"
            "max_retries_per_model: 2\n",
        )
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        from src.llm.manager import LLMManager

        mgr = LLMManager(config_path=cfg)
        assert not mgr._legacy_mode
        assert "prov-a" in mgr._providers
        assert "prov-b" in mgr._providers
        assert mgr._providers["prov-a"]["models"]["model-1"] == 0.5
        assert mgr._fallback_order == ["prov-a/model-1", "prov-b/model-2"]
        assert mgr._retry_on_error_codes == [1301, 500]
        assert mgr._max_retries_per_model == 2

    def test_legacy_mode_when_no_yaml(self, tmp_path):
        """No YAML → legacy_mode=True, uses .env vars."""
        nonexistent = tmp_path / "nonexistent.yaml"

        from src.llm.manager import LLMManager

        mgr = LLMManager(config_path=nonexistent)
        assert mgr._legacy_mode


# ---------------------------------------------------------------------------
# 2. Fallback logic
# ---------------------------------------------------------------------------

class TestFallback:
    def test_first_model_succeeds(self, tmp_path, monkeypatch):
        """First model works → returns its result."""
        cfg = tmp_path / "llm.yaml"
        _make_yaml_config(cfg, "fallback_order:\n  - prov-a/model-1\n  - prov-b/model-2\n")
        monkeypatch.setenv("OPENAI_API_KEY", "k")

        from src.llm.manager import LLMManager

        mgr = LLMManager(config_path=cfg)

        fake_response = AIMessage(content="ok from model-1")

        with patch.object(mgr, "_get_llm") as mock_get:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = fake_response
            mock_get.return_value = mock_llm

            result = mgr.invoke(_messages())
            assert result.content == "ok from model-1"
            mock_get.assert_called_once_with("prov-a", "model-1", 0.5)

    def test_fallback_on_retryable_error(self, tmp_path, monkeypatch):
        """First model fails with retryable error → second model tried."""
        cfg = tmp_path / "llm.yaml"
        _make_yaml_config(cfg, "fallback_order:\n  - prov-a/model-1\n  - prov-b/model-2\n")
        monkeypatch.setenv("OPENAI_API_KEY", "k")

        from src.llm.manager import LLMManager

        mgr = LLMManager(config_path=cfg)

        # First model raises with error code 1301
        err1 = Exception("content blocked")
        err1.code = 1301

        fake_ok = AIMessage(content="ok from model-2")

        with patch.object(mgr, "_get_llm") as mock_get:
            llm1 = MagicMock()
            llm1.invoke.side_effect = err1
            llm2 = MagicMock()
            llm2.invoke.return_value = fake_ok
            mock_get.side_effect = [llm1, llm2]

            result = mgr.invoke(_messages())
            assert result.content == "ok from model-2"
            assert mock_get.call_count == 2

    def test_all_models_fail_raises(self, tmp_path, monkeypatch):
        """All models fail → LLMFallbackError with all errors."""
        cfg = tmp_path / "llm.yaml"
        _make_yaml_config(cfg, "fallback_order:\n  - prov-a/model-1\n  - prov-b/model-2\n")
        monkeypatch.setenv("OPENAI_API_KEY", "k")

        from src.llm.manager import LLMManager, LLMFallbackError

        mgr = LLMManager(config_path=cfg)

        err1 = Exception("error1")
        err1.code = 1301
        err2 = Exception("error2")
        err2.code = 500

        with patch.object(mgr, "_get_llm") as mock_get:
            llm1 = MagicMock()
            llm1.invoke.side_effect = err1
            llm2 = MagicMock()
            llm2.invoke.side_effect = err2
            mock_get.side_effect = [llm1, llm2]

            with pytest.raises(LLMFallbackError) as exc_info:
                mgr.invoke(_messages())

            assert len(exc_info.value.errors) == 2

    def test_non_retryable_error_skips_immediately(self, tmp_path, monkeypatch):
        """Non-retryable error (e.g. auth 401) → skip without retry."""
        cfg = tmp_path / "llm.yaml"
        _make_yaml_config(
            cfg,
            "fallback_order:\n  - prov-a/model-1\n  - prov-b/model-2\n"
            "retry_on_error_codes: [1301, 500]\n"  # 401 not in list
            "max_retries_per_model: 3\n",
        )
        monkeypatch.setenv("OPENAI_API_KEY", "k")

        from src.llm.manager import LLMManager

        mgr = LLMManager(config_path=cfg)

        err = Exception("unauthorized")
        err.code = 401

        fake_ok = AIMessage(content="fallback ok")

        with patch.object(mgr, "_get_llm") as mock_get:
            llm1 = MagicMock()
            llm1.invoke.side_effect = err
            llm2 = MagicMock()
            llm2.invoke.return_value = fake_ok
            mock_get.side_effect = [llm1, llm2]

            result = mgr.invoke(_messages())
            assert result.content == "fallback ok"
            # model-1 invoked only once (no retry for non-retryable)
            assert llm1.invoke.call_count == 1


# ---------------------------------------------------------------------------
# 3. Backward compatibility (no YAML)
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    def test_legacy_invoke(self, tmp_path, monkeypatch):
        """Legacy mode delegates to env-based ChatOpenAI."""
        monkeypatch.setenv("OPENAI_API_BASE_URL", "https://legacy.example.com/v4")
        monkeypatch.setenv("OPENAI_API_KEY", "legacy-key")
        monkeypatch.setenv("OPENAI_MODEL", "legacy-model")

        from src.llm.manager import LLMManager

        mgr = LLMManager(config_path=tmp_path / "no.yaml")
        assert mgr._legacy_mode

        # Invoke should call ChatOpenAI directly
        fake = AIMessage(content="legacy response")
        with patch("src.llm.manager.ChatOpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.invoke.return_value = fake
            MockOpenAI.return_value = mock_instance

            result = mgr.invoke(_messages())
            assert result.content == "legacy response"
            MockOpenAI.assert_called_once()

    def test_get_llm_returns_chatopenai(self, tmp_path, monkeypatch):
        """get_llm() returns a ChatOpenAI for backward compat."""
        monkeypatch.setenv("OPENAI_API_BASE_URL", "https://x.com")
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        monkeypatch.setenv("OPENAI_MODEL", "m")

        from src.llm.manager import LLMManager

        mgr = LLMManager(config_path=tmp_path / "no.yaml")
        llm = mgr.get_llm(temperature=0.9)
        # Just check it's a ChatOpenAI-compatible object
        assert hasattr(llm, "invoke")
