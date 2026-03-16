#!/usr/bin/env python3
"""Tavily Search CLI — unified protocol provider."""

import os
import sys
import requests

# Allow running directly: add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.search.providers.protocol import parse_provider_args, emit_result, emit_error, make_result


SOURCE_NAME = "tavily"
API_URL = "https://api.tavily.com/search"


def search(query: str, max_results: int = 5, time_range: str = None) -> None:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        emit_error("TAVILY_API_KEY not set", SOURCE_NAME)
        sys.exit(1)

    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
    }
    if time_range:
        # Tavily uses topic + days mapping
        topic_map = {"week": "news", "month": "general", "year": "general"}
        payload["topic"] = topic_map.get(time_range, "general")
        if time_range == "week":
            payload["days"] = 7
        elif time_range == "month":
            payload["days"] = 30

    try:
        resp = requests.post(API_URL, json=payload, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        emit_error(f"Request failed: {e}", SOURCE_NAME)
        sys.exit(1)

    data = resp.json()
    for item in data.get("results", []):
        emit_result(make_result(
            title=item.get("title", ""),
            url=item.get("url", ""),
            content=item.get("content", ""),
            score=float(item.get("score", 0)),
            source=SOURCE_NAME,
        ))


def main():
    args = parse_provider_args()
    search(args.query, args.max_results, args.time_range)


if __name__ == "__main__":
    main()
