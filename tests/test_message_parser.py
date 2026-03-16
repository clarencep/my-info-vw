"""Tests for message parser agent."""

import pytest
from dotenv import load_dotenv

load_dotenv()

from src.agents.message_parser import MessageParserAgent, extract_json


@pytest.mark.needs_real_llm
def test_extract_json_with_code_block():
    """Test JSON extraction from code block."""
    response = '''```json
{
    "main_claim": "Test claim",
    "key_entities": ["Entity1", "Entity2"],
    "needs_verification": true
}
```'''
    result = extract_json(response)
    assert result is not None
    assert result["main_claim"] == "Test claim"
    assert len(result["key_entities"]) == 2


@pytest.mark.needs_real_llm
def test_extract_json_direct():
    """Test JSON extraction from direct JSON."""
    response = '{"main_claim": "Direct JSON", "key_entities": ["Test"]}'
    result = extract_json(response)
    assert result is not None
    assert result["main_claim"] == "Direct JSON"


@pytest.mark.needs_real_llm
def test_extract_json_invalid():
    """Test JSON extraction with invalid JSON."""
    response = "This is not JSON at all"
    result = extract_json(response)
    assert result is None


@pytest.mark.needs_real_llm
def test_extract_json_partial():
    """Test JSON extraction with partial JSON."""
    response = '{"main_claim": "Partial'
    result = extract_json(response)
    assert result is None


@pytest.mark.needs_real_llm
def test_message_parser_parse():
    """Test message parser parse method."""
    agent = MessageParserAgent()
    result = agent.parse("SpaceX 在 2026年发射了星舰")
    
    assert isinstance(result, dict)
    assert "main_claim" in result
    assert "key_entities" in result


@pytest.mark.needs_real_llm
def test_message_parser_factual():
    """Test parser with factual message."""
    agent = MessageParserAgent()
    result = agent.parse("苹果公司在2024年发布了iPhone 16")
    
    # Should return parsed result as dict
    assert isinstance(result, dict)
    assert "main_claim" in result


@pytest.mark.needs_real_llm
def test_message_parser_non_verifiable():
    """Test parser with non-verifiable message."""
    agent = MessageParserAgent()
    result = agent.parse("你好呀，今天天气真好！")
    
    # Should return parsed result
    assert isinstance(result, dict)
    assert "main_claim" in result
