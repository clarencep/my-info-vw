"""SearchProviderManager — config-driven multi-provider search aggregator.

Loads provider definitions from config/search.yaml, executes them in priority
order via the unified CLI protocol, and aggregates results with deduplication.
"""

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from src.search.providers.protocol import SearchResult, SearchError

logger = logging.getLogger(__name__)

# Re-usable regex for ${VAR} substitution
_ENV_VAR_RE = re.compile(r"\$\{([^}]+)\}")


class SearchProviderManager:
    """Manage and execute config-driven search providers."""

    def __init__(self, config_path: str | Path | None = None, project_root: str | Path | None = None):
        if config_path is None:
            if project_root:
                config_path = Path(project_root) / "config" / "search.yaml"
            else:
                # Walk up from this file to find config/
                config_path = Path(__file__).resolve().parent.parent.parent / "config" / "search.yaml"
        self.config_path = Path(config_path)
        self.project_root = Path(project_root) if project_root else self.config_path.parent.parent
        self._config: dict[str, Any] | None = None

    # ------------------------------------------------------------------ config

    def _resolve_env_value(self, value: str) -> str:
        """Replace ${VAR_NAME} patterns with os.getenv values."""
        def _replacer(m: re.Match) -> str:
            return os.getenv(m.group(1), "")
        return _ENV_VAR_RE.sub(_replacer, value)

    def _resolve_env_dict(self, env_dict: dict[str, str]) -> dict[str, str]:
        return {k: self._resolve_env_value(v) for k, v in env_dict.items()}

    def load_config(self) -> dict[str, Any]:
        """Load and return the search.yaml configuration."""
        if self._config is not None:
            return self._config

        if not self.config_path.exists():
            logger.warning("search.yaml not found at %s — using defaults", self.config_path)
            self._config = {"providers": [], "search_order": [], "max_results_per_provider": 5, "max_total_results": 15}
            return self._config

        with open(self.config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f) or {}

        logger.info("Loaded search config from %s", self.config_path)
        return self._config

    def _get_enabled_providers(self) -> list[dict[str, Any]]:
        """Return provider configs for enabled providers in search_order."""
        cfg = self.load_config()
        order = cfg.get("search_order", [])
        providers_map = {p["name"]: p for p in cfg.get("providers", [])}

        result = []
        for name in order:
            p = providers_map.get(name)
            if p and p.get("enabled", False):
                result.append(p)
        # Append any enabled providers not in search_order
        for p in cfg.get("providers", []):
            if p.get("enabled", False) and p["name"] not in order:
                result.append(p)
        return result

    # --------------------------------------------------------------- execution

    def _run_provider(self, provider: dict[str, Any], query: str,
                      max_results: int, time_range: str | None = None) -> list[SearchResult]:
        """Execute a single provider CLI and parse its JSONL output."""
        name = provider["name"]
        command = provider["command"]
        env_extra = self._resolve_env_dict(provider.get("env", {}) or {})

        cmd_path = Path(command)
        if not cmd_path.is_absolute():
            cmd_path = self.project_root / command
        executable = str(cmd_path)

        if not Path(executable).exists():
            logger.warning("[%s] CLI not found: %s", name, executable)
            return []

        cmd = [
            sys.executable if "python" in executable else executable,
            executable,
            "--query", query,
            "--max-results", str(max_results),
            "--output-format", "JSONL",
        ]
        # Fix: use python to run .py scripts
        if executable.endswith(".py"):
            cmd = [sys.executable, executable, "--query", query,
                   "--max-results", str(max_results), "--output-format", "JSONL"]
        if time_range:
            cmd.extend(["--time-range", time_range])

        logger.info("[%s] Running: %s", name, " ".join(cmd[:5]) + " ...")

        run_env = os.environ.copy()
        run_env.update(env_extra)

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
                cwd=str(self.project_root), env=run_env,
            )
        except subprocess.TimeoutExpired:
            logger.warning("[%s] Timed out", name)
            return []
        except Exception as exc:
            logger.warning("[%s] Execution error: %s", name, exc)
            return []

        if proc.stderr:
            logger.debug("[%s] stderr: %s", name, proc.stderr.strip())

        results: list[SearchResult] = []
        for line in proc.stdout.strip().splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("[%s] Invalid JSONL line: %s", name, line[:120])
                continue

            if obj.get("error"):
                logger.warning("[%s] Error: %s", name, obj.get("message", "unknown"))
                continue

            results.append(obj)  # type: ignore[assignment]

        logger.info("[%s] Returned %d results", name, len(results))
        return results

    # ----------------------------------------------------------------- public

    def search(self, query: str, max_total: int | None = None,
               max_per_provider: int | None = None,
               time_range: str | None = None) -> list[SearchResult]:
        """Search across enabled providers, deduplicate, and return results."""
        cfg = self.load_config()
        max_per = max_per_provider or cfg.get("max_results_per_provider", 5)
        max_total = max_total or cfg.get("max_total_results", 15)

        providers = self._get_enabled_providers()
        if not providers:
            logger.warning("No enabled search providers configured")
            return []

        all_results: list[SearchResult] = []
        for provider in providers:
            results = self._run_provider(provider, query, max_per, time_range)
            all_results.extend(results)

        # Deduplicate by URL
        seen: set[str] = set()
        unique: list[SearchResult] = []
        for r in all_results:
            url = r.get("url", "")
            if url not in seen:
                seen.add(url)
                unique.append(r)

        return unique[:max_total]



