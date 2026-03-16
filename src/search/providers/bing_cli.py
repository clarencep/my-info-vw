#!/usr/bin/env python3
"""Bing Web Search CLI — unified protocol provider.

Uses the Bing Web Search API: https://www.microsoft.com/en-us/bing/apis/bing-web-search-api
Requires BING_API_KEY environment variable (Azure Cognitive Services key).
"""

import os
import sys
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.search.providers.protocol import parse_provider_args, emit_result, emit_error, make_result


SOURCE_NAME = "bing"
API_URL = "https://api.bing.microsoft.com/v7.0/search"


def search(query: str, max_results: int = 5, time_range: str = None) -> None:
    api_key = os.getenv("BING_API_KEY")
    if not api_key:
        emit_error("BING_API_KEY not set", SOURCE_NAME)
        sys.exit(1)

    headers = {"Ocp-Apim-Subscription-Key": api_key}
    params = {"q": query, "count": max_results, "mkt": "zh-CN"}
    if time_range:
        fresh_map = {"week": "P7D", "month": "P30D", "year": "P365D"}
        params["freshness"] = fresh_map.get(time_range, "P7D")

    try:
        resp = requests.get(API_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        emit_error(f"Request failed: {e}", SOURCE_NAME)
        sys.exit(1)

    data = resp.json()
    web_pages = data.get("webPages", {}).get("value", [])
    for item in web_pages:
        emit_result(make_result(
            title=item.get("name", ""),
            url=item.get("url", ""),
            content=item.get("snippet", ""),
            score=float(item.get("relevanceScore", 0.8)),
            source=SOURCE_NAME,
        ))


def main():
    args = parse_provider_args()
    search(args.query, args.max_results, args.time_range)


if __name__ == "__main__":
    main()
