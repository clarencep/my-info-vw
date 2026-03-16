"""LLM Manager with multi-provider automatic fallback.

Supports YAML-based multi-model configuration with automatic degradation
on error codes (content moderation, rate limits, server errors).
Falls back to single .env model if no YAML config exists.
"""

import logging
import os
from pathlib import Path
from typing import Any, List, Optional, Sequence

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult
from langchain_openai import ChatOpenAI

load_dotenv()

logger = logging.getLogger(__name__)

# Default YAML config path
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "llm.yaml"


class LLMFallbackError(Exception):
    """All providers exhausted."""

    def __init__(self, errors: list[tuple[str, str, Exception]]):
        self.errors = errors  # [(provider, model, error), ...]
        details = "; ".join(f"{p}/{m}: {e}" for p, m, e in errors)
        super().__init__(f"All {len(errors)} model(s) failed: {details}")


class LLMManager:
    """Multi-provider LLM with automatic fallback."""

    def __init__(self, config_path: Optional[Path] = None):
        self._config_path = config_path or DEFAULT_CONFIG_PATH
        self._providers: dict[str, dict] = {}
        self._fallback_order: list[str] = []  # "provider/model"
        self._retry_on_error_codes: list[int] = []
        self._max_retries_per_model: int = 1
        self._llm_instances: dict[str, ChatOpenAI] = {}
        self._legacy_mode = False  # True when no YAML config

        self._load_config()

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
            api_key = os.getenv(prov.get("api_key_env", "OPENAI_API_KEY"), "")
            self._providers[name] = {
                "api_base": prov.get("api_base"),
                "api_key": api_key,
                "models": {m["name"]: m.get("temperature", 0.7) for m in prov.get("models", [])},
            }

        self._fallback_order = cfg.get("fallback_order", [])
        self._retry_on_error_codes = cfg.get("retry_on_error_codes", [1301, 1302, 429, 500, 503])
        self._max_retries_per_model = cfg.get("max_retries_per_model", 1)

        logger.info(
            "[LLM] loaded %d provider(s), fallback order: %s",
            len(self._providers),
            self._fallback_order,
        )

    # ------------------------------------------------------------------
    # LLM instance management
    # ------------------------------------------------------------------

    def _get_llm(self, provider_name: str, model_name: str, temperature: float = 0.7) -> ChatOpenAI:
        """Get or create a cached ChatOpenAI instance."""
        key = f"{provider_name}/{model_name}"
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
                        "[LLM] 尝试 %s/%s (attempt %d/%d) ...",
                        provider_name, model_name, attempt, self._max_retries_per_model,
                    )
                    result = llm.invoke(messages)
                    logger.info("[LLM] ✅ %s/%s 成功", provider_name, model_name)
                    return result

                except Exception as exc:
                    code = self._extract_error_code(exc)
                    reason = f"error_code={code}" if code is not None else str(exc)
                    logger.warning(
                        "[LLM] ❌ %s/%s 失败 (%s)",
                        provider_name, model_name, reason,
                    )
                    if not self._should_retry(exc):
                        errors.append((provider_name, model_name, exc))
                        break  # non-retryable → next model
                    # retryable → will retry if attempts remain
                    if attempt == self._max_retries_per_model:
                        errors.append((provider_name, model_name, exc))

        raise LLMFallbackError(errors)

    def get_llm(self, temperature: float = 0.7) -> ChatOpenAI:
        """Backward-compatible: return a single ChatOpenAI (first fallback entry or legacy).

        This allows existing code that expects `BaseAgent.__init__` to receive a ChatOpenAI
        to keep working unchanged.
        """
        if self._legacy_mode:
            return self._get_legacy_llm(temperature)

        # Return the first model in fallback_order
        first = self._fallback_order[0] if self._fallback_order else None
        if first and "/" in first:
            prov, model = first.split("/", 1)
            if prov in self._providers and model in self._providers[prov]["models"]:
                return self._get_llm(prov, model, temperature or self._providers[prov]["models"][model])

        # Last resort
        return self._get_legacy_llm(temperature)
