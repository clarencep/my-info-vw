"""Jina AI search integration."""

import os
import json
import requests
from typing import List, Dict, Any


class JinaSearch:
    """Jina AI web search client."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        self.base_url = "https://api.jina.ai/v1/search"
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search using Jina AI."""
        if not self.api_key:
            raise ValueError("JINA_API_KEY not provided")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": query,
            "max_results": max_results
        }
        
        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        results = data.get("data", [])
        
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", "")[:500],
                "score": 1.0
            }
            for r in results
        ]


def get_jina_client() -> JinaSearch:
    """Factory function."""
    return JinaSearch()
