"""Search module for info-check.

Available search clients:
- TavilySearch: General web search
- JinaSearch: AI-powered search
- NewsSearch: News articles
- SearchAggregator: Multi-channel search
"""

from .tavily_search import TavilySearch, get_search_client
from .jina_search import JinaSearch, get_jina_client
from .news_search import NewsSearch, get_news_client
from .aggregator import SearchAggregator, get_aggregator

__all__ = [
    "TavilySearch",
    "get_search_client",
    "JinaSearch",
    "get_jina_client",
    "NewsSearch",
    "get_news_client",
    "SearchAggregator",
    "get_aggregator",
]
