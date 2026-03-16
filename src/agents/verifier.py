"""Verification agent - analyzes search results and determines fact accuracy."""

import json
import re
from typing import TypedDict, List, Optional, Any
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


class SourceInfo(TypedDict):
    """Source information."""
    title: str
    url: str
    reliability: str


class VerificationResult(TypedDict):
    """Verification result structure."""
    verdict: str
    confidence: float
    supporting_evidence: List[str]
    contradicting_evidence: List[str]
    analysis: str
    sources: List[SourceInfo]
    raw_response: Optional[str]


def extract_json(response: str) -> Optional[dict]:
    """Safely extract JSON from LLM response."""
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        if end > start:
            try:
                return json.loads(response[start:end].strip())
            except json.JSONDecodeError:
                pass
    
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass
    
    # Try to find first complete JSON
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
    
    return None


class VerifierAgent(BaseAgent):
    """Agent that verifies facts based on search results."""
    
    def __init__(self):
        super().__init__(SYSTEM_PROMPT, temperature=0.3)
    
    def verify(self, message: str, search_results: List[dict]) -> VerificationResult:
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
        parsed = extract_json(response)
        if parsed:
            return VerificationResult(
                verdict=parsed.get("verdict", "UNVERIFIABLE"),
                confidence=float(parsed.get("confidence", 0.0)),
                supporting_evidence=parsed.get("supporting_evidence", []),
                contradicting_evidence=parsed.get("contradicting_evidence", []),
                analysis=parsed.get("analysis", ""),
                sources=parsed.get("sources", []),
                raw_response=None
            )
        
        # Fallback
        return VerificationResult(
            verdict="UNVERIFIABLE",
            confidence=0.0,
            supporting_evidence=[],
            contradicting_evidence=[],
            analysis="解析失败",
            sources=[],
            raw_response=response
        )
