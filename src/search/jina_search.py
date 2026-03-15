"""Jina AI search integration."""

import os
import json
import requests
from typing import List, Dict, Any


class JinaSearch:
    """Jina AI web search client using jina.ai reader."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("JINA_API_KEY")
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search using Jina AI Reader API."""
        # Use Jina's reader API which is free and doesn't need API key
        url = f"https://r.jina.ai/search/{query}"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse results
            data = response.json()
            results = data.get("results", [])[:max_results]
            
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:500],
                    "score": r.get("score", 0.8)
                }
                for r in results
            ]
        except Exception as e:
            # Fallback: try Google search via Jina
            return self._search_fallback(query, max_results)
    
    def _search_fallback(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Fallback search using textise dot iitty."""
        try:
            url = f"https://r.jina.ai/http://textise.net/showtext.aspx?strURL=https://www.google.com/search?q={query}"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                return [{
                    "title": f"Search results for: {query}",
                    "url": f"https://www.google.com/search?q={query}",
                    "content": response.text[:500],
                    "score": 0.5
                }]
        except:
            pass
        
        return []


def get_jina_client() -> JinaSearch:
    """Factory function."""
    return JinaSearch()
