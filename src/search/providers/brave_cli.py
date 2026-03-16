#!/usr/bin/env python3
"""Brave Search CLI — unified protocol provider.

Uses the Brave Web Search API: https://api.search.brave.com/
Requires BRAVE_API_KEY environment variable.
"""

import os
import sys
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.search.providers.protocol import parse_provider_args, emit_result, emit_error, make_result


SOURCE_NAME = "brave"
API_URL = "https://api.search.brave.com/res/v1/web/search"


def search(query: str, max_results: int = 5, time_range: str = None) -> None:
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        emit_error("BRAVE_API_KEY not set", SOURCE_NAME)
        sys.exit(1)

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
    }
    params = {"q": query, "count": max_results}
    if time_range:
        fresh_map = {"week": "pd", "month": "pm", "year": "py"}
        params["freshness"] = fresh_map.get(time_range, "pd")

    try:
        resp = requests.get(API_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        emit_error(f"Request failed: {e}", SOURCE_NAME)
        sys.exit(1)

    data = resp.json()
    web_results = data.get("web", {}).get("results", [])
    for item in web_results:
        emit_result(make_result(
            title=item.get("title", ""),
            url=item.get("url", ""),
            content=item.get("description", ""),
            score=float(item.get("relevance_score", 0.8)),
            source=SOURCE_NAME,
        ))


def main():
    args = parse_provider_args()
    search(args.query, args.max_results, args.time_range)


if __name__ == "__main__":
    main()
