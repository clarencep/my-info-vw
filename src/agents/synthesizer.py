"""Synthesis agent - produces final comprehensive report."""

from .base import BaseAgent

SYSTEM_PROMPT = """你是一个内容综合专家。你的任务是将所有分析结果整合成一份清晰、准确的核查报告。

请根据 verifier agent 的判断结果，生成一份用户友好的核查报告。

报告要求：
1. 标题清晰标明核查结论
2. 简要说明核查过程
3. 列出关键证据
4. 给出可信度评分
5. 如有需要，提供进一步核查的建议

请以Markdown格式返回报告。"""


class SynthesizerAgent(BaseAgent):
    """Agent that synthesizes final report."""
    
    def __init__(self):
        super().__init__(SYSTEM_PROMPT, temperature=0.5)
    
    def synthesize(
        self,
        original_message: str,
        parsed: dict,
        queries: list,
        verification: dict,
        search_results: list
    ) -> str:
        """Synthesize final report."""
        prompt = f"""请生成一份消息核查报告：

## 原消息
{original_message}

## 消息分析
- 主要主张: {parsed.get('main_claim', '')}
- 关键实体: {', '.join(parsed.get('key_entities', []))}
- 时间信息: {parsed.get('time_info', '未知')}

## 搜索查询
{', '.join([q.get('query', '') for q in queries])}

## 核查结果
- 判断: {verification.get('verdict', '未知')}
- 可信度: {verification.get('confidence', 0):.0%}
- 分析: {verification.get('analysis', '')}

## 证据
支持证据: {', '.join(verification.get('supporting_evidence', [])[:3])}
反驳证据: {', '.join(verification.get('contradicting_evidence', [])[:3])}

请生成最终报告。"""
        
        return self.run(prompt)
