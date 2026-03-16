#!/usr/bin/env python3
"""Jina Search CLI — unified protocol provider."""

import os
import sys
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.search.providers.protocol import parse_provider_args, emit_result, emit_error, make_result


SOURCE_NAME = "jina"
SEARCH_URL = "https://s.jina.ai/api/search"


def search(query: str, max_results: int = 5, time_range: str = None) -> None:
    api_key = os.getenv("JINA_API_KEY")
    if not api_key:
        emit_error("JINA_API_KEY not set", SOURCE_NAME)
        sys.exit(1)

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    params = {"q": query, "count": max_results}
    if time_range:
        params["tbs"] = time_range

    try:
        resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        emit_error(f"Request failed: {e}", SOURCE_NAME)
        sys.exit(1)

    try:
        data = resp.json()
    except ValueError as e:
        emit_error(f"Invalid JSON response: {e}", SOURCE_NAME)
        sys.exit(1)

    for item in data.get("data", []):
        emit_result(make_result(
            title=item.get("title", ""),
            url=item.get("url", ""),
            content=item.get("description", "") or item.get("content", ""),
            score=float(item.get("relevanceScore", 0.8)),
            source=SOURCE_NAME,
        ))


def main():
    args = parse_provider_args()
    search(args.query, args.max_results, args.time_range)


if __name__ == "__main__":
    main()
