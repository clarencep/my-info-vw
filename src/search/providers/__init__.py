"""Search provider CLIs and protocol definitions."""

from .protocol import (
    SearchResult,
    SearchError,
    parse_provider_args,
    emit_result,
    emit_error,
    make_result,
    ARG_QUERY,
    ARG_MAX_RESULTS,
    ARG_TIME_RANGE,
    ARG_OUTPUT_FORMAT,
    TIME_RANGE_VALUES,
    OUTPUT_FORMAT_JSONL,
    EXIT_OK,
    EXIT_ERROR,
)

__all__ = [
    "SearchResult",
    "SearchError",
    "parse_provider_args",
    "emit_result",
    "emit_error",
    "make_result",
    "ARG_QUERY",
    "ARG_MAX_RESULTS",
    "ARG_TIME_RANGE",
    "ARG_OUTPUT_FORMAT",
    "TIME_RANGE_VALUES",
    "OUTPUT_FORMAT_JSONL",
    "EXIT_OK",
    "EXIT_ERROR",
]
