"""Tests for configurable search providers (Issue #3)."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── Fixtures ─────────────────────────────────────────────────────────────

SAMPLE_CONFIG = {
    "providers": [
        {
            "name": "tavily",
            "enabled": True,
            "command": "src/search/providers/tavily_cli.py",
            "env": {"TAVILY_API_KEY": "${TAVILY_API_KEY}"},
            "description": "Tavily AI Search",
        },
        {
            "name": "jina",
            "enabled": True,
            "command": "src/search/providers/jina_cli.py",
            "env": {"JINA_API_KEY": "${JINA_API_KEY}"},
            "description": "Jina AI Search",
        },
        {
            "name": "brave",
            "enabled": False,
            "command": "src/search/providers/brave_cli.py",
            "env": {"BRAVE_API_KEY": "${BRAVE_API_KEY}"},
            "description": "Brave Web Search",
        },
    ],
    "search_order": ["tavily", "jina"],
    "max_results_per_provider": 5,
    "max_total_results": 15,
}


@pytest.fixture
def config_dir(tmp_path):
    """Create a temp directory with search.yaml."""
    cfg_path = tmp_path / "config"
    cfg_path.mkdir()
    with open(cfg_path / "search.yaml", "w") as f:
        yaml.dump(SAMPLE_CONFIG, f)
    return tmp_path


@pytest.fixture
def sample_jsonl():
    """Return sample JSONL output lines."""
    return [
        json.dumps({"title": "Result 1", "url": "https://example.com/1", "content": "Content 1", "score": 0.9, "source": "tavily"}),
        json.dumps({"title": "Result 2", "url": "https://example.com/2", "content": "Content 2", "score": 0.8, "source": "tavily"}),
        json.dumps({"error": True, "message": "rate limited", "source": "tavily"}),
        json.dumps({"title": "Result 3", "url": "https://example.com/1", "content": "Dup content", "score": 0.7, "source": "jina"}),
    ]


# ── Protocol Tests ───────────────────────────────────────────────────────

class TestProtocol:
    """Tests for CLI protocol definitions."""

    def test_parse_provider_args_defaults(self):
        from src.search.providers.protocol import parse_provider_args

        args = parse_provider_args(["--query", "test"])
        assert args.query == "test"
        assert args.max_results == 5
        assert args.time_range is None
        assert args.output_format == "JSONL"

    def test_parse_provider_args_full(self):
        from src.search.providers.protocol import parse_provider_args

        args = parse_provider_args(["--query", "hello", "--max-results", "3", "--time-range", "week", "--output-format", "JSONL"])
        assert args.query == "hello"
        assert args.max_results == 3
        assert args.time_range == "week"
        assert args.output_format == "JSONL"

    def test_make_result(self):
        from src.search.providers.protocol import make_result

        r = make_result("Title", "https://x.com", "Body", 0.9, "tavily")
        assert r["title"] == "Title"
        assert r["url"] == "https://x.com"
        assert r["score"] == 0.9
        assert r["source"] == "tavily"

    def test_emit_result_and_error(self, capsys):
        from src.search.providers.protocol import emit_result, emit_error, make_result

        emit_result(make_result("T", "https://t.com", "C", 0.5, "test"))
        emit_error("oops", "test")

        output = capsys.readouterr().out
        lines = [l for l in output.strip().splitlines() if l]
        assert len(lines) == 2

        obj1 = json.loads(lines[0])
        assert obj1["title"] == "T"
        assert "error" not in obj1

        obj2 = json.loads(lines[1])
        assert obj2["error"] is True
        assert obj2["message"] == "oops"


# ── YAML Config Tests ────────────────────────────────────────────────────

class TestConfigLoading:

    def test_load_config(self, config_dir):
        from src.search.provider_manager import SearchProviderManager

        mgr = SearchProviderManager(
            config_path=config_dir / "config" / "search.yaml",
            project_root=config_dir,
        )
        cfg = mgr.load_config()
        assert len(cfg["providers"]) == 3
        assert cfg["search_order"] == ["tavily", "jina"]
        assert cfg["max_results_per_provider"] == 5
        assert cfg["max_total_results"] == 15

    def test_load_missing_config(self):
        from src.search.provider_manager import SearchProviderManager

        with tempfile.TemporaryDirectory() as td:
            mgr = SearchProviderManager(config_path=Path(td) / "nope.yaml", project_root=td)
            cfg = mgr.load_config()
            assert cfg["providers"] == []
            assert cfg["max_results_per_provider"] == 5

    def test_enabled_providers_order(self, config_dir):
        from src.search.provider_manager import SearchProviderManager

        mgr = SearchProviderManager(
            config_path=config_dir / "config" / "search.yaml",
            project_root=config_dir,
        )
        enabled = mgr._get_enabled_providers()
        names = [p["name"] for p in enabled]
        # brave is disabled, only tavily and jina
        assert names == ["tavily", "jina"]


# ── Environment Variable Substitution ────────────────────────────────────

class TestEnvSubstitution:

    def test_resolve_env_value(self):
        from src.search.provider_manager import SearchProviderManager

        mgr = SearchProviderManager.__new__(SearchProviderManager)
        os.environ["__TEST_VAR_123__"] = "hello123"
        try:
            result = mgr._resolve_env_value("${__TEST_VAR_123__}")
            assert result == "hello123"
        finally:
            del os.environ["__TEST_VAR_123__"]

    def test_resolve_env_missing(self):
        from src.search.provider_manager import SearchProviderManager

        mgr = SearchProviderManager.__new__(SearchProviderManager)
        result = mgr._resolve_env_value("${__NONEXISTENT_VAR_999__}")
        assert result == ""

    def test_resolve_env_dict(self):
        from src.search.provider_manager import SearchProviderManager

        mgr = SearchProviderManager.__new__(SearchProviderManager)
        os.environ["__TEST_A__"] = "valA"
        try:
            result = mgr._resolve_env_dict({"KEY_A": "${__TEST_A__}", "KEY_B": "static"})
            assert result["KEY_A"] == "valA"
            assert result["KEY_B"] == "static"
        finally:
            del os.environ["__TEST_A__"]


# ── JSONL Parsing & Deduplication ───────────────────────────────────────

class TestJSONLParsing:

    def test_parse_valid_jsonl(self, sample_jsonl):
        """Simulate parsing JSONL output."""
        results = []
        errors = []
        for line in sample_jsonl:
            obj = json.loads(line)
            if obj.get("error"):
                errors.append(obj)
            else:
                results.append(obj)

        assert len(results) == 3
        assert len(errors) == 1

    def test_dedup_by_url(self, sample_jsonl):
        """URL-based deduplication."""
        results = [json.loads(l) for l in sample_jsonl if not json.loads(l).get("error")]
        seen = set()
        unique = []
        for r in results:
            url = r["url"]
            if url not in seen:
                seen.add(url)
                unique.append(r)
        # 2 results share url https://example.com/1 → only 2 unique
        assert len(unique) == 2
        assert unique[0]["url"] == "https://example.com/1"
        assert unique[1]["url"] == "https://example.com/2"

    def test_invalid_jsonl_line_skipped(self):
        """Non-JSON lines should be skipped gracefully."""
        lines = [
            json.dumps({"title": "OK", "url": "https://x.com", "content": "", "score": 0.5, "source": "t"}),
            "this is not json",
            json.dumps({"title": "Also OK", "url": "https://y.com", "content": "", "score": 0.5, "source": "t"}),
        ]
        results = []
        for line in lines:
            try:
                obj = json.loads(line)
                if not obj.get("error"):
                    results.append(obj)
            except json.JSONDecodeError:
                pass
        assert len(results) == 2


# ── Backward Compatibility ───────────────────────────────────────────────

class TestBackwardCompat:

    def test_aggregator_no_config(self):
        """Without search.yaml, SearchAggregator should use legacy clients."""
        from src.search.aggregator import SearchAggregator

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            with patch.object(SearchAggregator, "__init__", lambda self: None):
                agg = SearchAggregator()
                agg._config_path = td_path / "config" / "search.yaml"
                agg._use_provider_manager = agg._config_path.exists()
                agg._manager = None
                if not agg._use_provider_manager:
                    agg.clients = []
                    agg._init_clients()
                assert agg._use_provider_manager is False

    def test_aggregator_with_config(self, config_dir):
        """With search.yaml, SearchAggregator should use provider manager."""
        from src.search.aggregator import SearchAggregator

        cfg_path = config_dir / "config" / "search.yaml"
        with patch.object(SearchAggregator, "__init__", lambda self: None):
            agg = SearchAggregator()
            agg._config_path = cfg_path
            agg._use_provider_manager = agg._config_path.exists()
            agg._manager = None
            assert agg._use_provider_manager is True


# ── Provider Manager Integration ─────────────────────────────────────────

class TestProviderManager:

    def _make_provider_manager(self, config_dir):
        """Create manager with mocked _run_provider to skip file-existence check."""
        from src.search.provider_manager import SearchProviderManager

        mgr = SearchProviderManager(
            config_path=config_dir / "config" / "search.yaml",
            project_root=config_dir,
        )
        return mgr

    def test_search_with_mock_provider(self, config_dir):
        """Test search with mocked _run_provider."""
        from src.search.provider_manager import SearchProviderManager

        mgr = self._make_provider_manager(config_dir)

        mock_results = [
            {"title": "R1", "url": "https://a.com", "content": "C1", "score": 0.9, "source": "tavily"},
            {"title": "R2", "url": "https://b.com", "content": "C2", "score": 0.8, "source": "jina"},
        ]

        call_count = {"n": 0}

        def fake_run_provider(provider, query, max_results, time_range=None):
            idx = call_count["n"]
            call_count["n"] += 1
            return [mock_results[idx]] if idx < len(mock_results) else []

        with patch.object(mgr, "_run_provider", side_effect=fake_run_provider):
            results = mgr.search("test query", max_per_provider=2, max_total=10)

        assert len(results) == 2
        assert results[0]["title"] == "R1"
        assert results[1]["title"] == "R2"

    def test_search_dedup_across_providers(self, config_dir):
        """Deduplication across providers in manager.search()."""
        from src.search.provider_manager import SearchProviderManager

        mgr = self._make_provider_manager(config_dir)

        def fake_run_provider(provider, query, max_results, time_range=None):
            return [{"title": "X", "url": "https://a.com", "content": "Y", "score": 0.9, "source": provider["name"]}]

        with patch.object(mgr, "_run_provider", side_effect=fake_run_provider):
            results = mgr.search("test", max_per_provider=1, max_total=10)

        # Both providers return same URL → 1 unique result
        assert len(results) == 1

    def test_search_empty_providers(self, config_dir):
        """No enabled providers → empty results."""
        from src.search.provider_manager import SearchProviderManager

        # Create config with no enabled providers
        empty_cfg = {"providers": [], "search_order": [], "max_results_per_provider": 5, "max_total_results": 15}
        cfg_path = config_dir / "config" / "search.yaml"
        with open(cfg_path, "w") as f:
            yaml.dump(empty_cfg, f)

        mgr = SearchProviderManager(config_path=cfg_path, project_root=config_dir)
        results = mgr.search("test")
        assert results == []
