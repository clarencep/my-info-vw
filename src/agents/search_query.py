"""Search query generation agent - generates effective search queries for verification."""

from .base import BaseAgent

SYSTEM_PROMPT = """你是一个搜索专家。你的任务是基于需要验证的事实，生成有效的搜索查询语句。

根据已提取的消息分析结果，生成3-5个搜索查询，用于从多个角度验证信息的准确性。

要求：
1. 查询应该简洁、具体
2. 覆盖不同角度（官方来源、新闻报道、专家观点等）
3. 包含关键实体和时间信息
4. 用中文返回结果

请以JSON数组格式返回，格式如下：
{
    "queries": [
        {"query": "查询1", "purpose": "验证目的"},
        {"query": "查询2", "purpose": "验证目的"},
        ...
    ]
}"""


class SearchQueryAgent(BaseAgent):
    """Agent that generates search queries for verification."""
    
    def __init__(self):
        super().__init__(SYSTEM_PROMPT, temperature=0.7)
    
    def generate_queries(self, parsed_message: dict) -> list:
        """Generate search queries based on parsed message."""
        # Construct prompt with parsed message info
        prompt = f"""请基于以下消息分析结果，生成搜索查询：

主要主张: {parsed_message.get('main_claim', '')}
关键实体: {', '.join(parsed_message.get('key_entities', []))}
时间信息: {parsed_message.get('time_info', '未知')}
可验证事实: {', '.join(parsed_message.get('verifiable_facts', []))}
"""
        
        response = self.run(prompt)
        
        # Try to parse JSON
        import json
        import re
        
        json_match = re.search(r'\[[\s\S]*\]|\{[\s\S]*"queries"[\s\S]*\}', response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if isinstance(data, dict) and "queries" in data:
                    return data["queries"]
                elif isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass
        
        # Fallback: generate simple queries from entities
        entities = parsed_message.get('key_entities', [])
        if entities:
            return [{"query": e, "purpose": "验证实体"} for e in entities[:3]]
        
        return [{"query": parsed_message.get('main_claim', ''), "purpose": "一般搜索"}]
