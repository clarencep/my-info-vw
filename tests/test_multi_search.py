"""Tests for multi-channel search."""

import os
import pytest
from dotenv import load_dotenv

load_dotenv()


def test_search_aggregator_import():
    """Test aggregator can be imported."""
    from src.search.aggregator import SearchAggregator, get_aggregator
    assert SearchAggregator is not None
    assert get_aggregator is not None


def test_jina_search_import():
    """Test Jina search can be imported."""
    from src.search.jina_search import JinaSearch
    assert JinaSearch is not None


def test_news_search_import():
    """Test News search can be imported."""
    from src.search.news_search import NewsSearch
    assert NewsSearch is not None


@pytest.mark.needs_real_llm
def test_aggregator_creation():
    """Test aggregator can be created."""
    from src.search.aggregator import get_aggregator
    agg = get_aggregator()
    assert agg is not None
    assert len(agg.clients) > 0
    print(f"Active clients: {[c[0] for c in agg.clients]}")


def test_aggregator_search():
    """Test aggregator search functionality."""
    from src.search.aggregator import get_aggregator
    
    agg = get_aggregator()
    
    # This test may skip if no API keys
    if len(agg.clients) == 0:
        pytest.skip("No search clients available")
    
    results = agg.search_all("SpaceX Starship", max_per_source=1)
    assert isinstance(results, list)
    
    # Check result structure
    for r in results:
        assert "title" in r
        assert "url" in r
        assert "search_source" in r
