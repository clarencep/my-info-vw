"""Tests for verifier agent."""

import pytest
from dotenv import load_dotenv

load_dotenv()

from src.agents.verifier import VerifierAgent, extract_json


@pytest.mark.needs_real_llm
def test_verifier_extract_json():
    """Test JSON extraction in verifier."""
    response = '''```json
{
    "verdict": "TRUE",
    "confidence": 0.95,
    "analysis": "Test analysis"
}
```'''
    result = extract_json(response)
    assert result is not None
    assert result["verdict"] == "TRUE"


@pytest.mark.needs_real_llm
def test_verifier_verify_with_results():
    """Test verifier with search results."""
    agent = VerifierAgent()
    
    search_results = [
        {
            "title": "Test News",
            "url": "https://example.com",
            "content": "SpaceX launched Starship successfully"
        }
    ]
    
    result = agent.verify("SpaceX launched Starship", search_results)
    
    assert isinstance(result, dict)
    assert "verdict" in result
    assert "confidence" in result


@pytest.mark.needs_real_llm
def test_verifier_verify_empty_results():
    """Test verifier with empty results."""
    agent = VerifierAgent()
    
    result = agent.verify("Some claim", [])
    
    # Should return dict with verdict
    assert isinstance(result, dict)
    assert "verdict" in result


@pytest.mark.needs_real_llm
def test_verifier_verify_multiple_results():
    """Test verifier with multiple results."""
    agent = VerifierAgent()
    
    search_results = [
        {"title": "News 1", "url": "https://a.com", "content": "Confirmed"},
        {"title": "News 2", "url": "https://b.com", "content": "Confirmed"},
        {"title": "News 3", "url": "https://c.com", "content": "Confirmed"},
    ]
    
    result = agent.verify("Event happened", search_results)
    assert isinstance(result, dict)
    assert "verdict" in result
