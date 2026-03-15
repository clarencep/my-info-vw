"""Verification agent - analyzes search results and determines fact accuracy."""

from .base import BaseAgent

SYSTEM_PROMPT = """你是一个事实核查专家。你的任务是基于搜索结果，判断给定消息的准确性。

请分析提供的搜索结果，判断原消息中的事实是否：
- 真实 (TRUE)
- 虚假 (FALSE)  
- 部分真实 (PARTIALLY_TRUE)
- 无法确定 (UNVERIFIABLE)

判断标准：
1. 如果有权威来源（官方媒体、政府网站、权威机构）证实，则为 TRUE
2. 如果有权威来源证伪，则为 FALSE
3. 如果部分信息被证实，部分被证伪，则为 PARTIALLY_TRUE
4. 如果没有足够信息，则为 UNVERIFIABLE

请以JSON格式返回分析结果：
{
    "verdict": "TRUE/FALSE/PARTIALLY_TRUE/UNVERIFIABLE",
    "confidence": 0.0-1.0,
    "supporting_evidence": ["支持的证据1", "支持证据2"],
    "contradicting_evidence": ["反驳的证据1", "反驳证据2"],
    "analysis": "简短分析说明",
    "sources": [{"title": "来源标题", "url": "来源链接", "reliability": "高/中/低"}]
}

注意：如果没有搜索结果，请返回 UNVERIFIABLE。"""


class VerifierAgent(BaseAgent):
    """Agent that verifies facts based on search results."""
    
    def __init__(self):
        super().__init__(SYSTEM_PROMPT, temperature=0.3)
    
    def verify(self, message: str, search_results: list) -> dict:
        """Verify message against search results."""
        # Format search results
        results_text = "\n\n".join([
            f"标题: {r.get('title', '')}\n内容: {r.get('content', '')}\n来源: {r.get('url', '')}"
            for r in search_results[:5]
        ])
        
        prompt = f"""请核查以下消息的准确性：

原消息: {message}

搜索结果:
{results_text}

请分析并给出判断。"""
        
        response = self.run(prompt)
        
        # Try to parse JSON
        import json
        import re
        
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Fallback
        return {
            "verdict": "UNVERIFIABLE",
            "confidence": 0.0,
            "analysis": "解析失败",
            "raw_response": response
        }
