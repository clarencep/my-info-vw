"""Tests for search query agent."""

import pytest
from dotenv import load_dotenv

load_dotenv()

from src.agents.search_query import SearchQueryAgent


def test_search_query_agent_init():
    """Test search query agent initialization."""
    agent = SearchQueryAgent()
    assert agent is not None
    assert agent.llm is not None


def test_search_query_generation():
    """Test search query generation."""
    agent = SearchQueryAgent()
    
    parsed = {
        "main_claim": "SpaceX 发射了星舰",
        "key_entities": ["SpaceX", "星舰"],
        "time_info": "2026年"
    }
    
    queries = agent.generate_queries(parsed)
    
    assert isinstance(queries, list)
    assert len(queries) > 0


def test_search_query_with_empty_entities():
    """Test query generation with empty entities."""
    agent = SearchQueryAgent()
    
    parsed = {
        "main_claim": "Test claim",
        "key_entities": [],
        "time_info": None
    }
    
    queries = agent.generate_queries(parsed)
    assert isinstance(queries, list)


def test_search_query_fallback():
    """Test query generation fallback."""
    agent = SearchQueryAgent()
    
    parsed = {
        "main_claim": "Some claim",
        "key_entities": ["Entity1", "Entity2", "Entity3"],
        "time_info": "2025"
    }
    
    queries = agent.generate_queries(parsed)
    assert isinstance(queries, list)
    assert len(queries) > 0
