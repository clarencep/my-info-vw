"""Tests for agents module."""

import os
import pytest
from dotenv import load_dotenv

load_dotenv()


def test_base_agent_import():
    """Test base agent can be imported."""
    from src.agents.base import BaseAgent, get_llm_manager
    assert BaseAgent is not None
    assert get_llm_manager is not None


def test_get_llm():
    """Test LLM manager can be created and returns ChatOpenAI."""
    from src.agents.base import get_llm_manager
    from langchain_openai import ChatOpenAI
    mgr = get_llm_manager()
    llm = mgr.get_llm()
    assert isinstance(llm, ChatOpenAI)


def test_message_parser_agent():
    """Test message parser agent."""
    from src.agents.message_parser import MessageParserAgent
    agent = MessageParserAgent()
    assert agent is not None
    
    result = agent.parse("马斯克的 SpaceX 在2026年发射了星舰")
    assert isinstance(result, dict)
    assert "main_claim" in result


def test_search_query_agent():
    """Test search query generator."""
    from src.agents.search_query import SearchQueryAgent
    agent = SearchQueryAgent()
    assert agent is not None
    
    parsed = {
        "main_claim": "SpaceX 发射了星舰",
        "key_entities": ["SpaceX", "星舰"],
        "time_info": "2026年"
    }
    queries = agent.generate_queries(parsed)
    assert isinstance(queries, list)
    assert len(queries) > 0


def test_verifier_agent():
    """Test verifier agent."""
    from src.agents.verifier import VerifierAgent
    agent = VerifierAgent()
    assert agent is not None
    
    # Test with mock search results
    search_results = [
        {
            "title": "SpaceX launches Starship",
            "url": "https://example.com",
            "content": "SpaceX successfully launched Starship"
        }
    ]
    result = agent.verify("SpaceX launched Starship", search_results)
    assert isinstance(result, dict)
    assert "verdict" in result


def test_synthesizer_agent():
    """Test synthesizer agent."""
    from src.agents.synthesizer import SynthesizerAgent
    agent = SynthesizerAgent()
    assert agent is not None
    
    report = agent.synthesize(
        "Test message",
        {"main_claim": "Test"},
        [{"query": "test"}],
        {"verdict": "TRUE", "confidence": 0.9},
        []
    )
    assert isinstance(report, str)
    assert len(report) > 0
