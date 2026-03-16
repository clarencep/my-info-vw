"""Base agent configuration."""

import logging
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm.manager import LLMManager

logger = logging.getLogger(__name__)

# Global LLMManager (lazy singleton)
_llm_manager: Optional[LLMManager] = None


def get_llm_manager() -> LLMManager:
    """Get or create the global LLMManager."""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager


class BaseAgent:
    """Base agent with LLM and system prompt.

    Uses LLMManager for automatic multi-model fallback.
    Falls back to legacy .env single-model mode when no YAML config exists.
    """

    def __init__(self, system_prompt: str, temperature: float = 0.7):
        self.llm_manager = get_llm_manager()
        self.system_prompt = SystemMessage(content=system_prompt)
        self.temperature = temperature

    def run(self, user_message: str) -> str:
        """Run agent with user message."""
        messages = [self.system_prompt, HumanMessage(content=user_message)]
        response = self.llm_manager.invoke(messages, temperature=self.temperature)
        return response.content
