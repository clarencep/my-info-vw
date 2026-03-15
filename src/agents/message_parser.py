"""Message parser agent - analyzes and extracts key facts from the input message."""

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


class MessageParserAgent(BaseAgent):
    """Agent that parses and extracts key facts from messages."""
    
    def __init__(self):
        super().__init__(SYSTEM_PROMPT, temperature=0.3)
    
    def parse(self, message: str) -> dict:
        """Parse message and return structured analysis."""
        response = self.run(message)
        
        # Try to parse JSON from response
        import json
        import re
        
        # Look for JSON block
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Fallback: return raw response
        return {
            "main_claim": message,
            "key_entities": [],
            "time_info": None,
            "verifiable_facts": [],
            "needs_verification": True,
            "reason": "Parse failed, defaulting to verification",
            "raw_response": response
        }
