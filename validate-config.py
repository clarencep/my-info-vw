#!/usr/bin/env python3
"""Validate LLM and search configuration files.

Usage:
    python validate-config.py                # validate both LLM & search
    python validate-config.py --only-llm     # validate only LLM config
    python validate-config.py --only-search  # validate only search config
    python validate-config.py --no-live      # skip connectivity checks

Environment:
    MY_INFO_VW_CONFIG_DIR  — config directory (default: config/)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Load .env early so API key checks work correctly
load_dotenv(Path(__file__).resolve().parent / ".env")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RED = "\033[91m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _err(msg: str) -> None:
    print(f"{_RED}  ✗ {msg}{_RESET}")


def _ok(msg: str) -> None:
    print(f"{_GREEN}  ✓ {msg}{_RESET}")


def _warn(msg: str) -> None:
    print(f"{_YELLOW}  ⚠ {msg}{_RESET}")


def _section(title: str) -> None:
    print(f"\n{_BOLD}{title}{_RESET}")


def get_config_root() -> Path:
    """Return config root, respecting MY_INFO_VW_CONFIG_DIR."""
    env_dir = os.getenv("MY_INFO_VW_CONFIG_DIR")
    if env_dir:
        return Path(env_dir)
    # Project root = this script's parent
    return Path(__file__).resolve().parent / "config"


_ENV_VAR_RE = re.compile(r"\$\{([^}]+)\}")


def _collect_env_refs(value) -> list[str]:
    """Recursively collect ${VAR_NAME} references from a value."""
    refs: list[str] = []
    if isinstance(value, str):
        refs.extend(_ENV_VAR_RE.findall(value))
    elif isinstance(value, dict):
        for v in value.values():
            refs.extend(_collect_env_refs(v))
    elif isinstance(value, list):
        for item in value:
            refs.extend(_collect_env_refs(item))
    return refs


# ---------------------------------------------------------------------------
# LLM validation
# ---------------------------------------------------------------------------

def validate_llm(config_dir: Path, *, skip_live: bool = False) -> int:
    """Validate llm.yaml. Returns error count."""
    _section("LLM Configuration")
    errors = 0

    llm_path = config_dir / "llm.yaml"
    if not llm_path.exists():
        _err(f"Config file not found: {llm_path}")
        return 1

    # --- Load YAML ---
    try:
        with open(llm_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        _err(f"YAML parse error in {llm_path}: {exc}")
        return 1

    if not isinstance(cfg, dict):
        _err(f"llm.yaml root must be a dict, got {type(cfg).__name__}")
        return 1

    # --- Validate providers list ---
    providers = cfg.get("providers")
    if providers is None:
        _err("'providers' key is missing")
        errors += 1
        return errors
    if not isinstance(providers, list):
        _err(f"'providers' must be a list, got {type(providers).__name__}")
        errors += 1
        return errors
    if len(providers) == 0:
        _warn("'providers' is empty — no LLM providers configured")

    provider_names: set[str] = set()
    model_set: set[str] = set()  # "provider/model" combos

    for i, prov in enumerate(providers):
        prefix = f"providers[{i}]"

        if not isinstance(prov, dict):
            _err(f"{prefix}: must be a dict, got {type(prov).__name__}")
            errors += 1
            continue

        # name
        name = prov.get("name")
        if name is None or not isinstance(name, str) or not name.strip():
            _err(f"{prefix}: 'name' is required and must be a non-empty string")
            errors += 1
            continue
        if name in provider_names:
            _err(f"{prefix}: duplicate provider name '{name}'")
            errors += 1
            continue
        provider_names.add(name)

        # api_base
        api_base = prov.get("api_base")
        if api_base is None:
            _err(f"provider '{name}': 'api_base' is required")
            errors += 1
        elif not isinstance(api_base, str) or not api_base.startswith("http"):
            _err(f"provider '{name}': 'api_base' must be a valid HTTP(S) URL")
            errors += 1

        # api_key_env
        api_key_env = prov.get("api_key_env")
        if api_key_env is None or not isinstance(api_key_env, str) or not api_key_env.strip():
            _err(f"provider '{name}': 'api_key_env' is required and must be a non-empty string")
            errors += 1
        else:
            key_val = os.getenv(api_key_env, "")
            if not key_val:
                _warn(f"provider '{name}': env var ${api_key_env} is not set (live check will be skipped)")
            elif set(key_val.strip()) == {"*"}:
                _warn(f"provider '{name}': env var ${api_key_env} is a placeholder (all asterisks)")

        # models
        models = prov.get("models")
        if models is None:
            _err(f"provider '{name}': 'models' is required")
            errors += 1
        elif not isinstance(models, list):
            _err(f"provider '{name}': 'models' must be a list, got {type(models).__name__}")
            errors += 1
        elif len(models) == 0:
            _warn(f"provider '{name}': 'models' is empty")
        else:
            for j, model in enumerate(models):
                m_prefix = f"provider '{name}'.models[{j}]"
                if not isinstance(model, dict):
                    _err(f"{m_prefix}: must be a dict, got {type(model).__name__}")
                    errors += 1
                    continue
                model_name = model.get("name")
                if model_name is None or not isinstance(model_name, str) or not model_name.strip():
                    _err(f"{m_prefix}: 'name' is required and must be a non-empty string")
                    errors += 1
                    continue
                combo = f"{name}/{model_name}"
                if combo in model_set:
                    _err(f"{m_prefix}: duplicate model '{combo}'")
                    errors += 1
                model_set.add(combo)

                temp = model.get("temperature")
                if temp is not None and not isinstance(temp, (int, float)):
                    _err(f"{m_prefix}: 'temperature' must be a number, got {type(temp).__name__}")
                    errors += 1
                elif temp is not None and not (0.0 <= temp <= 2.0):
                    _warn(f"{m_prefix}: temperature {temp} is outside typical range [0.0, 2.0]")

        _ok(f"provider '{name}': static check passed")

    # --- Validate fallback_order ---
    fallback_order = cfg.get("fallback_order")
    if fallback_order is None:
        _warn("'fallback_order' is missing — LLM manager will use empty list")
    elif not isinstance(fallback_order, list):
        _err(f"'fallback_order' must be a list, got {type(fallback_order).__name__}")
        errors += 1
    else:
        for entry in fallback_order:
            if not isinstance(entry, str) or "/" not in entry:
                _err(f"fallback_order entry '{entry}' must be in 'provider/model' format")
                errors += 1
                continue
            prov, model = entry.split("/", 1)
            if prov not in provider_names:
                _err(f"fallback_order: provider '{prov}' not found in providers")
                errors += 1
            elif entry not in model_set:
                _err(f"fallback_order: model '{entry}' not found in provider definitions")
                errors += 1

    # --- Validate retry_on_error_codes ---
    retry_codes = cfg.get("retry_on_error_codes")
    if retry_codes is not None:
        if not isinstance(retry_codes, list):
            _err(f"'retry_on_error_codes' must be a list, got {type(retry_codes).__name__}")
            errors += 1
        else:
            for code in retry_codes:
                if not isinstance(code, int):
                    _err(f"'retry_on_error_codes': entry '{code}' must be an int")
                    errors += 1

    # --- Validate max_retries_per_model ---
    max_retries = cfg.get("max_retries_per_model")
    if max_retries is not None and not isinstance(max_retries, int):
        _err(f"'max_retries_per_model' must be an int, got {type(max_retries).__name__}")
        errors += 1

    # --- Light live check ---
    if skip_live:
        _section("LLM Live Connectivity (skipped --no-live)")
        return errors

    _section("LLM Live Connectivity (light)")
    if not providers:
        _warn("No providers to check")
        return errors

    for prov in providers:
        if not isinstance(prov, dict):
            continue
        name = prov.get("name", "")
        api_key_env = prov.get("api_key_env", "")
        api_key = os.getenv(api_key_env, "") if api_key_env else ""
        api_base = prov.get("api_base", "")
        models = prov.get("models") or []

        if not api_key or set(api_key.strip()) == {"*"}:
            _warn(f"provider '{name}': skipping live check (API key not available)")
            continue

        first_model = models[0].get("name") if models else None
        if not first_model:
            _warn(f"provider '{name}': no models defined, skipping live check")
            continue

        try:
            payload = json.dumps({
                "model": first_model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
                "temperature": 0,
            })
            proc = subprocess.run(
                [
                    "curl", "-s", "-w", "\n%{http_code}",
                    "-X", "POST",
                    f"{api_base}/chat/completions",
                    "-H", "Content-Type: application/json",
                    "-H", f"Authorization: Bearer {api_key}",
                    "-d", payload,
                    "--connect-timeout", "10",
                    "--max-time", "15",
                ],
                capture_output=True, text=True, timeout=20,
            )

            output = proc.stdout.strip()
            lines = output.rsplit("\n", 1)
            body = lines[0] if len(lines) > 1 else ""
            http_code = lines[-1] if len(lines) > 1 else "unknown"

            if proc.returncode != 0:
                _err(f"provider '{name}' ({first_model}): curl failed — {proc.stderr.strip()[:200]}")
                errors += 1
                continue

            if http_code.startswith("2"):
                _ok(f"provider '{name}' ({first_model}): live check passed (HTTP {http_code})")
            else:
                try:
                    err_body = json.loads(body)
                    msg = err_body.get("error", {}).get("message", body[:200])
                except (json.JSONDecodeError, AttributeError):
                    msg = body[:200]
                _err(f"provider '{name}' ({first_model}): HTTP {http_code} — {msg}")
                errors += 1

        except subprocess.TimeoutExpired:
            _err(f"provider '{name}' ({first_model}): timed out (20s)")
            errors += 1
        except Exception as exc:
            _err(f"provider '{name}' ({first_model}): {exc}")
            errors += 1

    return errors


# ---------------------------------------------------------------------------
# Search validation
# ---------------------------------------------------------------------------

def validate_search(config_dir: Path, *, skip_live: bool = False) -> int:
    """Validate search.yaml. Returns error count."""
    _section("Search Configuration")
    errors = 0

    search_path = config_dir / "search.yaml"
    if not search_path.exists():
        _err(f"Config file not found: {search_path}")
        return 1

    # --- Load YAML ---
    try:
        with open(search_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        _err(f"YAML parse error in {search_path}: {exc}")
        return 1

    if not isinstance(cfg, dict):
        _err(f"search.yaml root must be a dict, got {type(cfg).__name__}")
        return 1

    # --- Validate providers list ---
    providers = cfg.get("providers")
    if providers is None:
        _err("'providers' key is missing")
        errors += 1
        return errors
    if not isinstance(providers, list):
        _err(f"'providers' must be a list, got {type(providers).__name__}")
        errors += 1
        return errors

    project_root = Path(__file__).resolve().parent
    provider_names: set[str] = set()

    for i, prov in enumerate(providers):
        prefix = f"providers[{i}]"

        if not isinstance(prov, dict):
            _err(f"{prefix}: must be a dict, got {type(prov).__name__}")
            errors += 1
            continue

        # name
        name = prov.get("name")
        if name is None or not isinstance(name, str) or not name.strip():
            _err(f"{prefix}: 'name' is required and must be a non-empty string")
            errors += 1
            continue
        if name in provider_names:
            _err(f"{prefix}: duplicate provider name '{name}'")
            errors += 1
            continue
        provider_names.add(name)

        # enabled
        enabled = prov.get("enabled")
        if enabled is None:
            _warn(f"provider '{name}': 'enabled' not set, defaults to False")
        elif not isinstance(enabled, bool):
            _err(f"provider '{name}': 'enabled' must be a bool, got {type(enabled).__name__}")
            errors += 1

        # command
        command = prov.get("command")
        if command is None or not isinstance(command, str) or not command.strip():
            _err(f"provider '{name}': 'command' is required and must be a non-empty string")
            errors += 1
        else:
            cmd_path = Path(command)
            if not cmd_path.is_absolute():
                cmd_path = project_root / command
            if not cmd_path.exists():
                _err(f"provider '{name}': command file not found: {cmd_path}")
                errors += 1
            elif not os.access(cmd_path, os.X_OK) and not cmd_path.suffix == ".py":
                _warn(f"provider '{name}': command file is not executable: {cmd_path}")

        # env
        env_dict = prov.get("env")
        if env_dict is not None:
            if not isinstance(env_dict, dict):
                _err(f"provider '{name}': 'env' must be a dict, got {type(env_dict).__name__}")
                errors += 1
            else:
                for k, v in env_dict.items():
                    if not isinstance(k, str):
                        _err(f"provider '{name}'.env: key must be a string, got {type(k).__name__}")
                        errors += 1
                    if not isinstance(v, str):
                        _err(f"provider '{name}.env['{k}']: value must be a string, got {type(v).__name__}")
                        errors += 1
                    else:
                        refs = _ENV_VAR_RE.findall(v)
                        for ref in refs:
                            val = os.getenv(ref, "")
                            if not val:
                                _warn(f"provider '{name}': env ref ${{{ref}}} is not set")

        # description (optional, just type check)
        desc = prov.get("description")
        if desc is not None and not isinstance(desc, str):
            _err(f"provider '{name}': 'description' must be a string, got {type(desc).__name__}")
            errors += 1

        _ok(f"provider '{name}': static check passed")

    # --- Validate search_order ---
    search_order = cfg.get("search_order")
    if search_order is None:
        _warn("'search_order' is missing — defaulting to empty list")
    elif not isinstance(search_order, list):
        _err(f"'search_order' must be a list, got {type(search_order).__name__}")
        errors += 1
    else:
        for entry in search_order:
            if not isinstance(entry, str):
                _err(f"search_order entry must be a string, got {type(entry).__name__}")
                errors += 1
            elif entry not in provider_names:
                _err(f"search_order: provider '{entry}' not found in providers")
                errors += 1

    # --- Validate max_results_per_provider ---
    max_per = cfg.get("max_results_per_provider")
    if max_per is not None:
        if not isinstance(max_per, int) or max_per < 1:
            _err(f"'max_results_per_provider' must be a positive int, got {max_per}")
            errors += 1

    # --- Validate max_total_results ---
    max_total = cfg.get("max_total_results")
    if max_total is not None:
        if not isinstance(max_total, int) or max_total < 1:
            _err(f"'max_total_results' must be a positive int, got {max_total}")
            errors += 1

    # --- Light live check (enabled providers only) ---
    if skip_live:
        _section("Search Live Connectivity (skipped --no-live)")
        return errors

    _section("Search Live Connectivity (light)")
    enabled_providers = [
        p for p in providers
        if isinstance(p, dict) and p.get("enabled", False)
    ]

    if not enabled_providers:
        _warn("No enabled providers to check")
        return errors

    for prov in enabled_providers:
        name = prov.get("name", "")
        command = prov.get("command", "")

        if not command:
            _warn(f"provider '{name}': no command, skipping live check")
            continue

        cmd_path = Path(command)
        if not cmd_path.is_absolute():
            cmd_path = project_root / command

        if not cmd_path.exists():
            # Already reported in static check
            continue

        # Check if all required env vars are available
        env_refs = _collect_env_refs(prov.get("env") or {})
        missing_refs = [r for r in env_refs if not os.getenv(r, "")]
        if missing_refs:
            _warn(f"provider '{name}': skipping live check (env vars not set: {', '.join(missing_refs)})")
            continue

        # Resolve env vars for subprocess
        env_extra = prov.get("env") or {}
        resolved_env = {}
        for k, v in env_extra.items():
            resolved_env[k] = _ENV_VAR_RE.sub(
                lambda m: os.getenv(m.group(1), ""), str(v)
            )

        cli_cmd = [sys.executable, str(cmd_path), "--query", "test",
                   "--max-results", "1", "--output-format", "JSONL"]

        run_env = os.environ.copy()
        run_env.update(resolved_env)

        try:
            proc = subprocess.run(
                cli_cmd, capture_output=True, text=True, timeout=30,
                cwd=str(project_root), env=run_env,
            )

            if proc.returncode == 0:
                _ok(f"provider '{name}': live check passed (exit 0)")
            else:
                detail = ""
                if proc.stderr and proc.stderr.strip():
                    detail = proc.stderr.strip()[:200]
                if proc.stdout and proc.stdout.strip():
                    stdout_snippet = proc.stdout.strip()[:200]
                    detail = f"{detail} | {stdout_snippet}" if detail else stdout_snippet
                _err(f"provider '{name}': live check failed (exit {proc.returncode}) — {detail or '(no output)'}")
                errors += 1

        except subprocess.TimeoutExpired:
            _err(f"provider '{name}': timed out (30s)")
            errors += 1
        except Exception as exc:
            _err(f"provider '{name}': {exc}")
            errors += 1

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate my-info-vw configuration files (LLM & search)"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--only-llm", action="store_true",
                       help="Validate only LLM config (llm.yaml)")
    group.add_argument("--only-search", action="store_true",
                       help="Validate only search config (search.yaml)")
    parser.add_argument("--no-live", action="store_true",
                        help="Skip live connectivity checks (static validation only)")
    args = parser.parse_args()

    config_dir = get_config_root()

    if not config_dir.is_dir():
        print(f"{_RED}Config directory not found: {config_dir}{_RESET}")
        sys.exit(1)

    print(f"{_BOLD}Config directory: {config_dir}{_RESET}")
    if args.no_live:
        print(f"{_YELLOW}Live connectivity checks disabled (--no-live){_RESET}")

    total_errors = 0

    if args.only_search:
        total_errors += validate_search(config_dir, skip_live=args.no_live)
    elif args.only_llm:
        total_errors += validate_llm(config_dir, skip_live=args.no_live)
    else:
        total_errors += validate_llm(config_dir, skip_live=args.no_live)
        total_errors += validate_search(config_dir, skip_live=args.no_live)

    # --- Summary ---
    print()
    if total_errors == 0:
        print(f"{_GREEN}{_BOLD}All checks passed ✓ (0 errors){_RESET}")
        sys.exit(0)
    else:
        print(f"{_RED}{_BOLD}Validation failed: {total_errors} error(s) found{_RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
