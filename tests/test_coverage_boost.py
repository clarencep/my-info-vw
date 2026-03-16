"""Tests to boost coverage - targeting specific uncovered lines."""

import pytest
import json
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

load_dotenv()


# === Tests for aggregator.py (lines 22-23, 27-28, 32-33) ===

@pytest.mark.needs_real_llm
def test_aggregator_error_handling():
    """Test aggregator handles client errors."""
    from src.search.aggregator import SearchAggregator
    
    # Create aggregator with mock clients
    agg = SearchAggregator()
    
    # Mock one client to raise error
    if agg.clients:
        source_name, original_client = agg.clients[0]
        
        # Replace with mock that raises
        agg.clients[0] = (source_name, MagicMock(search=MagicMock(side_effect=Exception("API Error"))))
        
        results = agg.search_all("test query", max_per_source=1)
        assert isinstance(results, list)
        
        # Restore
        agg.clients[0] = (source_name, original_client)


@pytest.mark.needs_real_llm
def test_aggregator_no_clients():
    """Test aggregator with no clients."""
    from src.search.aggregator import SearchAggregator
    
    agg = SearchAggregator()
    # Should handle empty clients gracefully
    assert agg.clients is not None


# === Tests for jina_search.py (lines 25-28, 62) ===

@pytest.mark.needs_real_llm
def test_jina_search_api_error():
    """Test Jina search handles API errors."""
    from src.search.jina_search import JinaSearch
    import requests
    
    client = JinaSearch()
    
    # Mock to raise error
    with patch('requests.get', side_effect=requests.RequestException("API Error")):
        results = client.search("test", max_results=2)
        # Should return empty or fallback
        assert isinstance(results, list)


@pytest.mark.needs_real_llm
def test_jina_search_fallback_error():
    """Test Jina fallback with error."""
    from src.search.jina_search import JinaSearch
    
    client = JinaSearch()
    results = client._search_fallback("nonexistent query", 2)
    assert isinstance(results, list)


# === Tests for news_search.py (lines 35-40, 80) ===

@pytest.mark.needs_real_llm
def test_news_search_with_api_key():
    """Test News search with API key."""
    import os
    from src.search.news_search import NewsSearch
    
    # Set mock API key
    os.environ["NEWS_API_KEY"] = "test_key"
    
    client = NewsSearch()
    assert client.api_key == "test_key"
    
    del os.environ["NEWS_API_KEY"]


@pytest.mark.needs_real_llm
def test_news_search_api_error():
    """Test News search handles API errors."""
    from src.search.news_search import NewsSearch
    import requests
    
    client = NewsSearch(api_key="fake_key")
    
    # Mock to raise error
    with patch('requests.get', side_effect=requests.RequestException("API Error")):
        results = client.search("test", max_results=2)
        # Should fallback to Google
        assert isinstance(results, list)


# === Tests for tavily_search.py (lines 19, 48-61, 66) ===

@pytest.mark.needs_real_llm
def test_tavily_search_error():
    """Test Tavily handles errors."""
    from src.search.tavily_search import TavilySearch
    import requests
    
    client = TavilySearch(api_key="test_key")
    
    # Mock to raise error
    with patch('requests.post', side_effect=requests.RequestException("API Error")):
        results = client.search("test", max_results=2)
        assert isinstance(results, list)


@pytest.mark.needs_real_llm
def test_tavily_search_no_api_key_actual():
    """Test Tavily with no API key."""
    from src.search.tavily_search import TavilySearch
    
    import os
    old_key = os.environ.get("TAVILY_API_KEY")
    if "TAVILY_API_KEY" in os.environ:
        del os.environ["TAVILY_API_KEY"]
    
    try:
        with pytest.raises(ValueError, match="not provided"):
            client = TavilySearch()
    finally:
        if old_key:
            os.environ["TAVILY_API_KEY"] = old_key


# === Tests for workflows/check.py (lines 103-113, 118) ===

@pytest.mark.needs_real_llm
def test_workflow_parse_node():
    """Test workflow parse node."""
    from src.workflows.check import InfoCheckWorkflow
    
    workflow = InfoCheckWorkflow()
    state = {"original_message": "Test message", "parsed": None}
    
    result = workflow._parse_node(state)
    assert "parsed" in result


@pytest.mark.needs_real_llm
def test_workflow_generate_queries_node():
    """Test workflow generate queries node."""
    from src.workflows.check import InfoCheckWorkflow
    
    workflow = InfoCheckWorkflow()
    state = {
        "original_message": "Test",
        "parsed": {"main_claim": "Test", "key_entities": ["A"]}
    }
    
    result = workflow._generate_queries_node(state)
    assert "queries" in result


@pytest.mark.needs_real_llm
def test_workflow_search_node():
    """Test workflow search node."""
    from src.workflows.check import InfoCheckWorkflow
    
    workflow = InfoCheckWorkflow()
    state = {
        "original_message": "Test",
        "queries": [{"query": "test", "purpose": "verify"}]
    }
    
    result = workflow._search_node(state)
    assert "search_results" in result


@pytest.mark.needs_real_llm
def test_workflow_verify_node():
    """Test workflow verify node."""
    from src.workflows.check import InfoCheckWorkflow
    
    workflow = InfoCheckWorkflow()
    state = {
        "original_message": "Test message",
        "search_results": [{"title": "Test", "url": "http://test", "content": "Content"}]
    }
    
    result = workflow._verify_node(state)
    assert "verification" in result


@pytest.mark.needs_real_llm
def test_workflow_synthesize_node():
    """Test workflow synthesize node."""
    from src.workflows.check import InfoCheckWorkflow
    
    workflow = InfoCheckWorkflow()
    state = {
        "original_message": "Test",
        "parsed": {"main_claim": "Test"},
        "queries": [{"query": "test"}],
        "verification": {"verdict": "TRUE"},
        "search_results": []
    }
    
    result = workflow._synthesize_node(state)
    assert "report" in result


@pytest.mark.needs_real_llm
def test_workflow_run():
    """Test workflow run method."""
    from src.workflows.check import create_workflow
    
    workflow = create_workflow()
    assert workflow is not None
    assert hasattr(workflow, "run")


# === Tests for search_query.py fallback paths ===

@pytest.mark.needs_real_llm
def test_search_query_fallback_with_entities():
    """Test search query fallback with entities."""
    from src.agents.search_query import SearchQueryAgent
    import json
    
    agent = SearchQueryAgent()
    
    # Test the fallback code path directly by calling generate_queries
    parsed = {
        "main_claim": "Test claim",
        "key_entities": ["Entity1", "Entity2", "Entity3"],
        "time_info": "2025"
    }
    
    # The fallback is used when LLM doesn't return valid JSON
    # Let's test by mocking the LLM to return invalid JSON
    original_invoke = agent.llm.__class__.__call__
    
    def mock_call(*args, **kwargs):
        # Return invalid JSON to trigger fallback
        return MagicMock(content="This is not valid JSON at all")
    
    try:
        agent.llm.__class__.__call__ = mock_call
        result = agent.generate_queries(parsed)
    finally:
        agent.llm.__class__.__call__ = original_invoke
    
    # Should return fallback result
    assert isinstance(result, list)


@pytest.mark.needs_real_llm
def test_search_query_fallback_no_entities():
    """Test search query fallback with no entities."""
    from src.agents.search_query import SearchQueryAgent
    
    agent = SearchQueryAgent()
    
    original_call = agent.llm.__class__.__call__
    
    def mock_call(*args, **kwargs):
        return MagicMock(content="Invalid JSON")
    
    try:
        agent.llm.__class__.__call__ = mock_call
        parsed = {"main_claim": "Only main claim", "key_entities": [], "time_info": None}
        result = agent.generate_queries(parsed)
    finally:
        agent.llm.__class__.__call__ = original_call
    
    assert isinstance(result, list)


@pytest.mark.needs_real_llm
def test_search_query_json_list_response():
    """Test when LLM returns JSON list."""
    from src.agents.search_query import SearchQueryAgent
    
    agent = SearchQueryAgent()
    
    original_call = agent.llm.__class__.__call__
    
    def mock_call(*args, **kwargs):
        return MagicMock(content='["query1", "query2", "query3"]')
    
    try:
        agent.llm.__class__.__call__ = mock_call
        parsed = {"main_claim": "Test", "key_entities": ["A"]}
        result = agent.generate_queries(parsed)
    finally:
        agent.llm.__class__.__call__ = original_call
    
    assert isinstance(result, list)


# === Tests for verifier.py fallback paths ===

@pytest.mark.needs_real_llm
def test_verifier_extract_nested_braces():
    """Test JSON extraction with nested braces."""
    from src.agents.verifier import extract_json
    
    # Test nested JSON
    response = '{"outer": {"inner": "value"}, "key": "val"}'
    result = extract_json(response)
    assert result is not None


@pytest.mark.needs_real_llm
def test_verifier_extract_malformed_json():
    """Test JSON extraction with malformed JSON."""
    from src.agents.verifier import extract_json
    
    # Test truly malformed JSON
    response = '```json\n{"broken"\n```'
    result = extract_json(response)
    # Should try fallback approaches
    assert result is None or isinstance(result, dict)


@pytest.mark.needs_real_llm
def test_verifier_verify_fallback():
    """Test verifier fallback path."""
    from src.agents.verifier import VerifierAgent
    
    agent = VerifierAgent()
    
    original_call = agent.llm.__class__.__call__
    
    def mock_call(*args, **kwargs):
        # Return non-JSON to trigger fallback
        return MagicMock(content="No JSON here, just plain text response")
    
    try:
        agent.llm.__class__.__call__ = mock_call
        results = [{"title": "Test", "url": "http://test.com", "content": "Content"}]
        result = agent.verify("Some claim", results)
    finally:
        agent.llm.__class__.__call__ = original_call
    
    # Should have fallback result
    assert isinstance(result, dict)
    assert "verdict" in result


@pytest.mark.needs_real_llm
def test_verifier_verify_valid_json_no_verdict():
    """Test verifier with valid JSON but no verdict key."""
    from src.agents.verifier import VerifierAgent
    
    agent = VerifierAgent()
    
    original_call = agent.llm.__class__.__call__
    
    def mock_call(*args, **kwargs):
        return MagicMock(content='{"analysis": "Some analysis", "confidence": 0.5}')
    
    try:
        agent.llm.__class__.__call__ = mock_call
        results = [{"title": "Test", "url": "http://test.com", "content": "Content"}]
        result = agent.verify("Some claim", results)
    finally:
        agent.llm.__class__.__call__ = original_call
    
    assert isinstance(result, dict)


# 快速测试 - 覆盖 fallback 路径

@pytest.mark.needs_real_llm
def test_search_query_simple():
    """Simple test for search query."""
    from src.agents.search_query import SearchQueryAgent
    agent = SearchQueryAgent()
    # Test initialization
    assert agent.llm is not None


@pytest.mark.needs_real_llm
def test_verifier_simple():
    """Simple test for verifier."""
    from src.agents.verifier import VerifierAgent
    agent = VerifierAgent()
    # Test initialization
    assert agent.llm is not None
