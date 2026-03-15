"""Tests for search channels."""

import os
import pytest
from dotenv import load_dotenv

load_dotenv()


def test_tavily_search_with_api():
    """Test Tavily search with actual API."""
    from src.search.tavily_search import TavilySearch
    
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        pytest.skip("TAVILY_API_KEY not set")
    
    client = TavilySearch(api_key)
    results = client.search("test query", max_results=3)
    
    assert isinstance(results, list)
    assert len(results) <= 3
    
    for r in results:
        assert "title" in r
        assert "url" in r
        assert "content" in r


def test_tavily_search_sync():
    """Test Tavily search sync method."""
    from src.search.tavily_search import TavilySearch
    
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        pytest.skip("TAVILY_API_KEY not set")
    
    client = TavilySearch(api_key)
    output = client.search_sync("Starship", max_results=2)
    
    assert isinstance(output, str)
    assert "搜索结果" in output or "No results" in output


def test_jina_search():
    """Test Jina search."""
    from src.search.jina_search import JinaSearch
    
    client = JinaSearch()
    results = client.search("SpaceX", max_results=2)
    
    assert isinstance(results, list)


def test_jina_search_fallback():
    """Test Jina search fallback."""
    from src.search.jina_search import JinaSearch
    
    client = JinaSearch()
    results = client._search_fallback("test query", 2)
    
    assert isinstance(results, list)


def test_news_search_init():
    """Test News search initialization."""
    from src.search.news_search import NewsSearch
    
    client = NewsSearch()
    assert client is not None
    assert client.base_url == "https://newsapi.org/v2"


def test_news_search_fallback():
    """Test news search fallback to Google RSS."""
    from src.search.news_search import NewsSearch
    
    client = NewsSearch()
    results = client._search_via_google("technology", 3)
    
    # May return empty if feedparser not available
    assert isinstance(results, list)


def test_aggregator_all_sources():
    """Test aggregator with all sources."""
    from src.search.aggregator import get_aggregator
    
    agg = get_aggregator()
    results = agg.search_all("artificial intelligence", max_per_source=1)
    
    assert isinstance(results, list)
    
    # Check source tagging
    for r in results:
        assert "search_source" in r


def test_aggregator_parallel():
    """Test aggregator parallel search."""
    from src.search.aggregator import get_aggregator
    
    agg = get_aggregator()
    results = agg.search_parallel(["test query 1", "test query 2"], max_per_source=1)
    
    assert isinstance(results, list)
