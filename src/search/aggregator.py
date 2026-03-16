"""Multi-channel search aggregator."""

from typing import List, Dict, Any
import asyncio

from .tavily_search import TavilySearch
from .jina_search import JinaSearch
from .news_search import NewsSearch


class SearchAggregator:
    """Aggregates results from multiple search sources."""
    
    def __init__(self):
        self.clients = []
        self._init_clients()
    
    def _init_clients(self):
        """Initialize available search clients."""
        try:
            self.clients.append(("tavily", TavilySearch()))
        except Exception as e:
            print(f"Tavily not available: {e}")
        
        try:
            self.clients.append(("jina", JinaSearch()))
        except Exception as e:
            print(f"Jina not available: {e}")
        
        try:
            self.clients.append(("news", NewsSearch()))
        except Exception as e:
            print(f"News not available: {e}")
    
    def search_all(self, query: str, max_per_source: int = 3) -> List[Dict[str, Any]]:
        """Search across all available sources."""
        all_results = []
        
        for source_name, client in self.clients:
            try:
                results = client.search(query, max_results=max_per_source)
                
                # Add source tag to each result
                for r in results:
                    r["search_source"] = source_name
                
                all_results.extend(results)
                print(f"[{source_name}] Found {len(results)} results")
                
            except Exception as e:
                print(f"[{source_name}] Error: {e}")
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        
        for r in all_results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)
        
        return unique_results
    
    def search_parallel(self, queries: List[str], max_per_source: int = 2) -> List[Dict[str, Any]]:
        """Search multiple queries across all sources."""
        all_results = []
        
        for query in queries:
            results = self.search_all(query, max_per_source)
            all_results.extend(results)
        
        return all_results


def get_aggregator() -> SearchAggregator:
    """Factory function."""
    return SearchAggregator()
