"""LLM Manager with multi-provider automatic fallback.

Supports YAML-based multi-model configuration with automatic degradation
on error codes (content moderation, rate limits, server errors).
Falls back to single .env model if no YAML config exists.
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, List, Optional, Sequence

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult
from langchain_openai import ChatOpenAI

load_dotenv()

logger = logging.getLogger(__name__)


def get_default_config_path() -> Path:
    """Return the default config path, respecting MY_INFO_VW_CONFIG_DIR."""
    from src.config import get_config_root
    return get_config_root() / "llm.yaml"


# Module-level default for backward compat (e.g. tests that read DEFAULT_CONFIG_PATH)
DEFAULT_CONFIG_PATH = get_default_config_path()


class LLMFallbackError(Exception):
    """All providers exhausted."""

    def __init__(self, errors: list[tuple[str, str, Exception]]):
        self.errors = errors  # [(provider, model, error), ...]
        details = "; ".join(f"{p}/{m}: {e}" for p, m, e in errors)
        super().__init__(f"All {len(errors)} model(s) failed: {details}")


class LLMManager:
    """Multi-provider LLM with automatic fallback."""

    def __init__(self, config_path: Optional[Path] = None):
        self._config_path = config_path or get_default_config_path()
        self._providers: dict[str, dict] = {}
        self._fallback_order: list[str] = []  # "provider/model"
        self._retry_on_error_codes: list[int] = []
        self._max_retries_per_model: int = 1
        self._llm_instances: dict[str, ChatOpenAI] = {}
        self._lock = threading.Lock()
        self._legacy_mode = False  # True when no YAML config

        self._load_config()

    # ------------------------------------------------------------------
    # API key resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_api_key(env_key: str) -> str:
        """Resolve API key for a provider.

        Resolution order:
        1. The env var specified by ``api_key_env`` (e.g. ``BIGMODEL_API_KEY``).
        2. If ``api_key_env`` is *not* ``OPENAI_API_KEY`` and the above is empty,
           fall back to ``OPENAI_API_KEY`` for backward compatibility.

        This allows projects to migrate from the legacy ``OPENAI_API_KEY`` to
        provider-specific names without breaking existing deployments.
        """
        api_key = os.getenv(env_key, "")
        if not api_key and env_key != "OPENAI_API_KEY":
            api_key = os.getenv("OPENAI_API_KEY", "")
            if api_key:
                logger.info(
                    "[LLM] env var %s not set, using OPENAI_API_KEY as fallback "
                    "(set %s to silence this message)",
                    env_key, env_key,
                )
        return api_key

    # ------------------------------------------------------------------
    # Configuration loading
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        """Load YAML config if exists, otherwise fall back to .env."""
        import yaml  # lazy import – only needed here

        if not self._config_path.exists():
            logger.info("[LLM] config not found at %s, using .env single-model mode", self._config_path)
            self._legacy_mode = True
            return

        with open(self._config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        # Parse providers
        for prov in cfg.get("providers", []):
            name = prov["name"]
            env_key = prov.get("api_key_env", "OPENAI_API_KEY")
            api_key = self._resolve_api_key(env_key)

            # [P0] API Key pre-check
            if not api_key:
                logger.warning(
                    "[LLM] API key not set for provider '%s' (env var: %s), skipping",
                    name, env_key,
                )
                continue

            self._providers[name] = {
                "api_base": prov.get("api_base"),
                "api_key": api_key,
                "models": {m["name"]: m.get("temperature", 0.7) for m in prov.get("models", [])},
            }

        self._fallback_order = cfg.get("fallback_order", [])
        self._retry_on_error_codes = cfg.get("retry_on_error_codes", [1301, 1302, 429, 500, 503])
        self._max_retries_per_model = cfg.get("max_retries_per_model", 1)

        # [LOW] Validate fallback_order entries
        for entry in self._fallback_order:
            if "/" not in entry:
                logger.error("[LLM] invalid fallback_order entry (missing '/'): %s", entry)
                continue
            prov, model = entry.split("/", 1)
            if prov not in self._providers:
                logger.error("[LLM] fallback_order references unknown provider: %s", prov)
            elif model not in self._providers[prov]["models"]:
                logger.error("[LLM] fallback_order references unknown model: %s/%s", prov, model)

        logger.info(
            "[LLM] loaded %d provider(s), fallback order: %s",
            len(self._providers),
            self._fallback_order,
        )

    # ------------------------------------------------------------------
    # LLM instance management
    # ------------------------------------------------------------------

    def _get_llm(self, provider_name: str, model_name: str, temperature: float = 0.7) -> ChatOpenAI:
        """Get or create a cached ChatOpenAI instance (thread-safe)."""
        key = f"{provider_name}/{model_name}"
        with self._lock:
            if key not in self._llm_instances:
                prov = self._providers[provider_name]
                self._llm_instances[key] = ChatOpenAI(
                    openai_api_base=prov["api_base"],
                    openai_api_key=prov["api_key"],
                    model=model_name,
                    temperature=temperature,
                )
            return self._llm_instances[key]

    def _get_legacy_llm(self, temperature: float = 0.7) -> ChatOpenAI:
        """Single-model mode from .env."""
        return ChatOpenAI(
            openai_api_base=os.getenv("OPENAI_API_BASE_URL"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL", "glm-4.7"),
            temperature=temperature,
        )

    # ------------------------------------------------------------------
    # Error handling helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_error_code(exc: Exception) -> Optional[int]:
        """Extract error code from various exception types."""
        # OpenAI SDK / langchain wraps errors differently
        error_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        if error_code is not None:
            return int(error_code)

        # Check for structured error body
        response = getattr(exc, "response", None)
        if response is not None:
            body = getattr(response, "body", None) or getattr(response, "json", lambda: {})()
            if isinstance(body, dict):
                ec = body.get("error", {}).get("code")
                if ec is not None:
                    return int(ec)
        return None

    def _should_retry(self, exc: Exception) -> bool:
        """Check if the exception is retryable (in error code list)."""
        code = self._extract_error_code(exc)
        if code is not None and code in self._retry_on_error_codes:
            return True
        # Also retry on connection errors
        exc_type = type(exc).__name__.lower()
        for tag in ("connectionerror", "timeout", "apiconnectedclosed"):
            if tag in exc_type:
                return True
        return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def invoke(
        self,
        messages: Sequence[BaseMessage],
        temperature: Optional[float] = None,
    ) -> BaseMessage:
        """Invoke LLM with automatic fallback across providers/models.

        Args:
            messages: LangChain message sequence.
            temperature: Override temperature (default from config).

        Returns:
            The first AIMessage from the successful response.

        Raises:
            LLMFallbackError: when all models fail.
        """
        if self._legacy_mode:
            llm = self._get_legacy_llm(temperature or 0.7)
            logger.info("[LLM] legacy mode: %s", os.getenv("OPENAI_MODEL", "glm-4.7"))
            return llm.invoke(messages)

        errors: list[tuple[str, str, Exception]] = []

        for entry in self._fallback_order:
            if "/" not in entry:
                continue
            provider_name, model_name = entry.split("/", 1)

            if provider_name not in self._providers or model_name not in self._providers[provider_name]["models"]:
                logger.warning("[LLM] skip unknown %s/%s", provider_name, model_name)
                continue

            temp = temperature or self._providers[provider_name]["models"][model_name]
            llm = self._get_llm(provider_name, model_name, temp)

            for attempt in range(1, self._max_retries_per_model + 1):
                try:
                    logger.info(
                        "[LLM] trying %s/%s (attempt %d/%d) ...",
                        provider_name, model_name, attempt, self._max_retries_per_model,
                    )
                    result = llm.invoke(messages)
                    logger.info("[LLM] %s/%s succeeded", provider_name, model_name)
                    return result

                except Exception as exc:
                    code = self._extract_error_code(exc)
                    reason = f"error_code={code}" if code is not None else str(exc)
                    logger.warning(
                        "[LLM] %s/%s failed (%s)",
                        provider_name, model_name, reason,
                    )
                    if not self._should_retry(exc):
                        # [P0 Fix] Always append errors
                        errors.append((provider_name, model_name, exc))
                        break  # non-retryable -> next model
                    # retryable
                    errors.append((provider_name, model_name, exc))
                    # [P1] Exponential backoff before retry
                    if attempt < self._max_retries_per_model:
                        wait = min(2 ** (attempt - 1), 30)
                        logger.info("[LLM] retrying in %ds ...", wait)
                        time.sleep(wait)

        raise LLMFallbackError(errors)

    def get_llm(self, temperature: float = 0.7) -> ChatOpenAI:
        """Backward-compatible: return a single ChatOpenAI (first fallback entry or legacy)."""
        if self._legacy_mode:
            return self._get_legacy_llm(temperature)

        first = self._fallback_order[0] if self._fallback_order else None
        if first and "/" in first:
            prov, model = first.split("/", 1)
            if prov in self._providers and model in self._providers[prov]["models"]:
                return self._get_llm(prov, model, temperature or self._providers[prov]["models"][model])

        return self._get_legacy_llm(temperature)

    def health_check(self) -> dict[str, str]:
        """Check availability of all configured providers/models.

        Returns dict of "provider/model" -> "ok" | "error: reason".
        """
        results: dict[str, str] = {}
        from langchain_core.messages import HumanMessage

        if self._legacy_mode:
            model = os.getenv("OPENAI_MODEL", "glm-4.7")
            try:
                llm = self._get_legacy_llm()
                llm.invoke([HumanMessage(content="hi")])
                results[f"legacy/{model}"] = "ok"
            except Exception as e:
                results[f"legacy/{model}"] = f"error: {e}"
            return results

        for entry in self._fallback_order:
            if "/" not in entry:
                continue
            prov, model = entry.split("/", 1)
            if prov not in self._providers or model not in self._providers[prov]["models"]:
                results[entry] = "error: not configured"
                continue
            try:
                temp = self._providers[prov]["models"][model]
                llm = self._get_llm(prov, model, temp)
                llm.invoke([HumanMessage(content="hi")])
                results[entry] = "ok"
            except Exception as e:
                results[entry] = f"error: {e}"

        return results
