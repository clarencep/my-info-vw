"""Tests for search module."""

import os
import pytest
from dotenv import load_dotenv

load_dotenv()


def test_tavily_search_import():
    """Test Tavily search can be imported."""
    from src.search.tavily_search import TavilySearch
    assert TavilySearch is not None


def test_search_client_factory():
    """Test factory function."""
    from src.search.tavily_search import get_search_client
    client = get_search_client()
    assert client is not None


@pytest.mark.skipif(
    not os.getenv("TAVILY_API_KEY"),
    reason="TAVILY_API_KEY not set"
)
def test_search_execution():
    """Test actual search execution."""
    from src.search.tavily_search import get_search_client
    client = get_search_client()
    results = client.search("SpaceX Starship", max_results=2)
    assert isinstance(results, list)
    assert len(results) > 0
    
    # Check result structure
    for r in results:
        assert "title" in r
        assert "url" in r
        assert "content" in r
