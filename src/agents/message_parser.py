"""Message parser agent - analyzes and extracts key facts from the input message."""

import json
import re
from typing import TypedDict, Optional, List
from .base import BaseAgent

SYSTEM_PROMPT = """你是一个消息分析专家。你的任务是从用户提供的消息中提取出需要进行事实核查的关键信息。

请分析消息并提取：
1. 消息的核心主张/事实
2. 涉及的关键实体（人物、地点、组织、事件等）
3. 时间信息
4. 任何可验证的具体数据

请以结构化的JSON格式返回分析结果，格式如下：
{
    "main_claim": "主要主张/事实",
    "key_entities": ["实体1", "实体2", ...],
    "time_info": "时间信息（如果有）",
    "verifiable_facts": ["可验证的事实1", "可验证的事实2", ...],
    "needs_verification": true/false,
    "reason": "为什么需要/不需要验证的简短解释"
}

如果消息只是闲聊或明显是玩笑话，不需要验证。"""


class ParsedMessage(TypedDict):
    """Parsed message structure."""
    main_claim: str
    key_entities: List[str]
    time_info: Optional[str]
    verifiable_facts: List[str]
    needs_verification: bool
    reason: str
    raw_response: Optional[str]


def extract_json(response: str) -> Optional[dict]:
    """Safely extract JSON from LLM response."""
    # Try to extract ```json ... ``` block
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        if end > start:
            try:
                return json.loads(response[start:end].strip())
            except json.JSONDecodeError:
                pass
    
    # Try to find first complete JSON object
    brace_count = 0
    start_idx = None
    for i, char in enumerate(response):
        if char == '{':
            if start_idx is None:
                start_idx = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx is not None:
                try:
                    return json.loads(response[start_idx:i+1])
                except json.JSONDecodeError:
                    pass
    
    # Try direct parse
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass
    
    return None


class MessageParserAgent(BaseAgent):
    """Agent that parses and extracts key facts from messages."""
    
    def __init__(self):
        super().__init__(SYSTEM_PROMPT, temperature=0.3)
    
    def parse(self, message: str) -> ParsedMessage:
        """Parse message and return structured analysis."""
        response = self.run(message)
        
        # Try to parse JSON from response
        parsed = extract_json(response)
        if parsed:
            return ParsedMessage(
                main_claim=parsed.get("main_claim", message),
                key_entities=parsed.get("key_entities", []),
                time_info=parsed.get("time_info"),
                verifiable_facts=parsed.get("verifiable_facts", []),
                needs_verification=parsed.get("needs_verification", True),
                reason=parsed.get("reason", ""),
                raw_response=None
            )
        
        # Fallback: return raw response
        return ParsedMessage(
            main_claim=message,
            key_entities=[],
            time_info=None,
            verifiable_facts=[],
            needs_verification=True,
            reason="Parse failed, defaulting to verification",
            raw_response=response
        )
