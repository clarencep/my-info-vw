"""Multi-channel search aggregator."""

import logging
from typing import List, Dict, Any
from pathlib import Path

from .tavily_search import TavilySearch
from .jina_search import JinaSearch
from .news_search import NewsSearch

logger = logging.getLogger(__name__)


class SearchAggregator:
    """Aggregates results from multiple search sources.

    When config/search.yaml exists, uses SearchProviderManager for config-driven
    provider execution. Falls back to the legacy hard-coded clients otherwise.
    """

    def __init__(self):
        from src.config import get_config_root, get_project_root

        self._config_path = get_config_root() / "search.yaml"
        self._use_provider_manager = self._config_path.exists()
        self._manager = None
        self._project_root = get_project_root()
        self.clients = []
        if not self._use_provider_manager:
            self._init_clients()

    def _init_clients(self):
        """Initialize available search clients (legacy path)."""
        try:
            self.clients.append(("tavily", TavilySearch()))
        except Exception as e:
            logger.warning("Tavily not available: %s", e)

        try:
            self.clients.append(("jina", JinaSearch()))
        except Exception as e:
            logger.warning("Jina not available: %s", e)

        try:
            self.clients.append(("news", NewsSearch()))
        except Exception as e:
            logger.warning("News not available: %s", e)

    @property
    def provider_manager(self):
        """Lazy-load SearchProviderManager."""
        if self._manager is None and self._use_provider_manager:
            from .provider_manager import SearchProviderManager
            self._manager = SearchProviderManager(
                config_path=self._config_path,
                project_root=self._project_root,
            )
        return self._manager

    def search_all(self, query: str, max_per_source: int = 3) -> List[Dict[str, Any]]:
        """Search across all available sources."""
        if self._use_provider_manager:
            return self.provider_manager.search(query, max_per_provider=max_per_source)

        # Legacy path
        all_results = []
        for source_name, client in self.clients:
            try:
                results = client.search(query, max_results=max_per_source)
                for r in results:
                    r["search_source"] = source_name
                all_results.extend(results)
                logger.info("[%s] Found %d results", source_name, len(results))
            except Exception as e:
                logger.error("[%s] Error: %s", source_name, e)

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
