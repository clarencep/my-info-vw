"""Unified search provider CLI protocol definitions."""

import argparse
import json
import sys
from typing import TypedDict, Optional


class SearchResult(TypedDict):
    """Standard search result format output by provider CLIs."""
    title: str
    url: str
    content: str
    score: float
    source: str


class SearchError(TypedDict):
    """Standard error format output by provider CLIs."""
    error: bool
    message: str
    source: str


# CLI argument names
ARG_QUERY = "--query"
ARG_MAX_RESULTS = "--max-results"
ARG_TIME_RANGE = "--time-range"
ARG_OUTPUT_FORMAT = "--output-format"

# Valid time range values
TIME_RANGE_VALUES = ["week", "month", "year"]

# Output format
OUTPUT_FORMAT_JSONL = "JSONL"

# Exit codes
EXIT_OK = 0
EXIT_ERROR = 1


def parse_provider_args(argv: list[str] = None) -> argparse.Namespace:
    """Parse standard provider CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Search provider CLI (unified protocol)"
    )
    parser.add_argument(ARG_QUERY, required=True, help="Search query string")
    parser.add_argument(ARG_MAX_RESULTS, type=int, default=5, help="Max results to return")
    parser.add_argument(ARG_TIME_RANGE, choices=TIME_RANGE_VALUES, default=None, help="Time range filter")
    parser.add_argument(ARG_OUTPUT_FORMAT, choices=[OUTPUT_FORMAT_JSONL], default=OUTPUT_FORMAT_JSONL, help="Output format")
    return parser.parse_args(argv)


def emit_result(result: SearchResult) -> None:
    """Emit a single search result as JSONL to stdout."""
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


def emit_error(message: str, source: str) -> None:
    """Emit a search error as JSONL to stdout."""
    error: SearchError = {"error": True, "message": message, "source": source}
    json.dump(error, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


def make_result(title: str, url: str, content: str, score: float, source: str) -> SearchResult:
    """Helper to create a SearchResult dict."""
    return {
        "title": title,
        "url": url,
        "content": content,
        "score": score,
        "source": source,
    }
