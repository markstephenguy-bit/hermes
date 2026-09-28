#!/usr/bin/env python3
"""MCP server giving Hermes real web search + page-fetch tools.

Exists to stop the fallback behavior of shelling out to `curl` + regex
scraping on every research-shaped request (see catalog entity
hermes-research-lacks-web-search-tool-2026-09-27) - that path burns dozens
of tool calls and still gets blocked by bot detection on many sites.

web_search uses the Brave Search API (free tier: 2,000 queries/mo).
fetch_url uses the r.jina.ai Reader proxy (free, no key) to turn any page
into clean markdown instead of raw HTML/JS.
"""
import os

import httpx
from fastmcp import FastMCP

BRAVE_API_KEY = os.environ["BRAVE_API_KEY"]

mcp = FastMCP(name="search")


@mcp.tool
def web_search(query: str, count: int = 5) -> list[dict]:
    """Search the web and return title/url/snippet results."""
    resp = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": count},
        headers={"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY},
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json().get("web", {}).get("results", [])
    return [
        {"title": r.get("title"), "url": r.get("url"), "snippet": r.get("description")}
        for r in results
    ]


@mcp.tool
def fetch_url(url: str) -> str:
    """Fetch a URL and return its content as clean markdown/text."""
    resp = httpx.get(f"https://r.jina.ai/{url}", timeout=30)
    resp.raise_for_status()
    return resp.text


if __name__ == "__main__":
    mcp.run()
