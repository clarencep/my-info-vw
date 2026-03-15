"""Tavily search integration for info checking."""

import os
import json
from typing import List, Dict, Any
import requests


class TavilySearch:
    """Tavily search client."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.base_url = "https://api.tavily.com/search"
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for query and return results."""
        if not self.api_key:
            raise ValueError("Tavily API key not provided")
        
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": True,
            "include_raw_content": False,
            "include_images": False
        }
        
        response = requests.post(self.base_url, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
                "score": r.get("score", 0)
            }
            for r in results
        ]
    
    def search_sync(self, query: str, max_results: int = 5) -> str:
        """Search and return formatted string."""
        results = self.search(query, max_results)
        
        if not results:
            return f"No results found for: {query}"
        
        output = [f"搜索结果 ({len(results)} 条) - 查询: {query}\n"]
        
        for i, r in enumerate(results, 1):
            output.append(f"\n--- 结果 {i} ---")
            output.append(f"标题: {r['title']}")
            output.append(f"来源: {r['url']}")
            output.append(f"内容: {r['content'][:500]}...")
        
        return "\n".join(output)


def get_search_client() -> TavilySearch:
    """Factory function to get search client."""
    return TavilySearch()
