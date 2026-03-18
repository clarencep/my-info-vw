#!/usr/bin/env python3
"""Zhipu Web Search CLI — unified protocol provider.

Uses zai-sdk to call Zhipu AI Web Search API for improved Chinese search coverage.
"""

import os
import sys

# Allow running directly: add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.search.providers.protocol import parse_provider_args, emit_result, emit_error, make_result

SOURCE_NAME = "zhipu-web-search"

# Time range mapping to Zhipu API recency filters
TIME_RANGE_MAP = {
    "week": "oneWeek",
    "month": "oneMonth",
    "year": "oneYear",
}


def search(query: str, max_results: int = 5, time_range: str = None) -> None:
    api_key = os.getenv("ZHIPU_API_KEY")
    if not api_key:
        emit_error("ZHIPU_API_KEY not set", SOURCE_NAME)
        sys.exit(1)

    try:
        from zai import ZhipuAiClient
    except ImportError:
        emit_error("zai-sdk not installed. Run: pip install zai-sdk", SOURCE_NAME)
        sys.exit(1)

    client = ZhipuAiClient(api_key=api_key)

    kwargs = {
        "search_engine": "search_pro",
        "search_query": query,
        "count": max_results,
        "content_size": "high",
    }

    if time_range and time_range in TIME_RANGE_MAP:
        kwargs["search_recency_filter"] = TIME_RANGE_MAP[time_range]

    try:
        response = client.web_search.web_search(**kwargs)
    except Exception as e:
        emit_error(f"Zhipu API request failed: {e}", SOURCE_NAME)
        sys.exit(1)

    # Parse response — adapt to actual API response structure
    for item in getattr(response, "web_results", []) or getattr(response, "data", []) or []:
        emit_result(make_result(
            title=getattr(item, "title", "") or item.get("title", ""),
            url=getattr(item, "link", "") or item.get("link", "") or getattr(item, "url", "") or item.get("url", ""),
            content=getattr(item, "content", "") or item.get("content", "") or getattr(item, "snippet", "") or item.get("snippet", ""),
            score=getattr(item, "score", 0.7) or item.get("score", 0.7) or 0.7,
            source=SOURCE_NAME,
        ))


def main():
    args = parse_provider_args()
    search(args.query, args.max_results, args.time_range)


if __name__ == "__main__":
    main()
