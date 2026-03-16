#!/usr/bin/env python3
"""Baidu Search CLI — unified protocol provider.

Scrapes Baidu search results via HTTP. No API key needed.
"""

import os
import sys
import re
import json
import urllib.parse
import urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.search.providers.protocol import parse_provider_args, emit_result, emit_error, make_result


SOURCE_NAME = "baidu"
BAIDU_URL = "https://www.baidu.com/s"


class _BaiduParser(HTMLParser):
    """Minimal parser to extract Baidu search results."""

    def __init__(self):
        super().__init__()
        self.results: list[dict] = []
        self._in_result = False
        self._in_title = False
        self._in_content = False
        self._current: dict = {}
        self._tag_stack: list[str] = []
        self._data_buf = ""

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        self._tag_stack.append(tag)
        attrs_dict = dict(attrs)

        # Detect result container
        cls = attrs_dict.get("class", "")
        if "result" in cls or "c-container" in cls:
            self._in_result = True
            self._current = {"url": attrs_dict.get("href", ""), "title": "", "content": ""}

        if self._in_result:
            if tag == "h3":
                self._in_title = True
                self._data_buf = ""
            elif tag == "span" and "content-right_" in cls:
                self._in_content = True
                self._data_buf = ""

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()

        if self._in_result:
            if tag == "h3" and self._in_title:
                self._current["title"] = self._data_buf.strip()
                self._in_title = False
            elif tag == "span" and self._in_content:
                self._current["content"] = self._data_buf.strip()
                self._in_content = False

        # End of result block on next result div or end of document
        if self._in_result and tag == "div":
            cls_match = False
            # simple heuristic: emit when we have title + url
            if self._current.get("title") and self._current.get("url"):
                self.results.append(dict(self._current))
                self._current = {}
                self._in_result = False

    def handle_data(self, data):
        if self._in_title or self._in_content:
            self._data_buf += data


def search(query: str, max_results: int = 5, time_range: str = None) -> None:
    params = {"wd": query, "rn": str(max_results), "pn": "0"}
    if time_range:
        params["gpc"] = f"stf={time_range}"  # approximate

    url = f"{BAIDU_URL}?{urllib.parse.urlencode(params)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        emit_error(f"Request failed: {e}", SOURCE_NAME)
        sys.exit(1)

    parser = _BaiduParser()
    try:
        parser.feed(html)
    except Exception:
        pass

    for item in parser.results[:max_results]:
        clean_url = item.get("url", "")
        if clean_url.startswith("/"):
            clean_url = "https://www.baidu.com" + clean_url
        emit_result(make_result(
            title=item.get("title", ""),
            url=clean_url,
            content=item.get("content", ""),
            score=0.7,
            source=SOURCE_NAME,
        ))


def main():
    args = parse_provider_args()
    search(args.query, args.max_results, args.time_range)


if __name__ == "__main__":
    main()
