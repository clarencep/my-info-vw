"""Base agent configuration."""

import os
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    """Get configured LLM instance."""
    return ChatOpenAI(
        openai_api_base=os.getenv("OPENAI_API_BASE_URL"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL", "glm-4.7"),
        temperature=temperature,
    )


class BaseAgent:
    """Base agent with LLM and system prompt."""
    
    def __init__(self, system_prompt: str, temperature: float = 0.7):
        self.llm = get_llm(temperature)
        self.system_prompt = SystemMessage(content=system_prompt)
    
    def run(self, user_message: str) -> str:
        """Run agent with user message."""
        messages = [self.system_prompt, HumanMessage(content=user_message)]
        response = self.llm.invoke(messages)
        return response.content
