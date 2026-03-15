"""News search integration using NewsAPI."""

import os
import requests
from typing import List, Dict, Any
from datetime import datetime, timedelta


class NewsSearch:
    """News API client for fetching news articles."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("NEWS_API_KEY")
        self.base_url = "https://newsapi.org/v2"
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for news articles."""
        if not self.api_key:
            # Fallback: try to search via Google News RSS
            return self._search_via_google(query, max_results)
        
        params = {
            "apiKey": self.api_key,
            "q": query,
            "pageSize": max_results,
            "language": "zh"  # Prioritize Chinese news
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/everything",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            articles = data.get("articles", [])
            
            return [
                {
                    "title": a.get("title", ""),
                    "url": a.get("url", ""),
                    "content": a.get("description", ""),
                    "source": a.get("source", {}).get("name", ""),
                    "publishedAt": a.get("publishedAt", ""),
                    "score": 0.8
                }
                for a in articles
            ]
        except Exception:
            return self._search_via_google(query, max_results)
    
    def _search_via_google(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Fallback: search via Google News RSS."""
        import feedparser
        
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=zh-CN"
        
        try:
            feed = feedparser.parse(rss_url)
            
            results = []
            for entry in feed.entries[:max_results]:
                results.append({
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "content": entry.get("summary", ""),
                    "source": entry.get("source", {}).get("title", "Google News"),
                    "publishedAt": entry.get("published", ""),
                    "score": 0.7
                })
            return results
        except Exception:
            return []


def get_news_client() -> NewsSearch:
    """Factory function."""
    return NewsSearch()
