#!/usr/bin/env python3
"""MCP server giving Hermes real web search + page-fetch tools.

Exists to stop the fallback behavior of shelling out to `curl` + regex
scraping on every research-shaped request (see catalog entity
hermes-research-lacks-web-search-tool-2026-09-27) - that path burns dozens
of tool calls and still gets blocked by bot detection on many sites.

web_search uses the Brave Search API (free tier: 2,000 queries/mo).
fetch_page uses the r.jina.ai Reader proxy (free, no key) to turn any page
into clean markdown instead of raw HTML/JS.

KNOWN ISSUE: the model never recognizes the page-fetch tool as available,
regardless of its name (tried fetch_url, fetch_page, read_page_markdown) or
its position among the server's tools (tried first, middle, last) - only
web_search is ever actually usable. This looks like a Hermes-side registry
bug/collision, not something fixable here. See catalog entity
hermes-search-mcp-tool-selection-inconsistent-2026-09-28 for the full trail.
web_search alone still resolves the original problem (blind URL-guessing);
the model falls back to terminal/curl for the rare single-page fetch, which
is a small, targeted call instead of the dozens it used to burn searching.

fetch_page routes through the home Squid proxy (server:3128) rather than
calling r.jina.ai directly: hermes-vps's own network (Vultr, AS20473) got
IP-reputation-blocked by jina.ai ("anonymous queries... bad network
reputation", HTTP 401) - confirmed live 2026-09-28. Proxying through the
home network's residential-reputation egress sidesteps it without needing
a jina.ai account/API key.
"""
import os

import httpx
from fastmcp import FastMCP

BRAVE_API_KEY = os.environ["BRAVE_API_KEY"]
EGRESS_PROXY = "http://192.168.40.2:3128"

mcp = FastMCP(name="search")


@mcp.tool
def fetch_page(url: str) -> str:
    """Fetch a URL and return its content as clean markdown/text."""
    resp = httpx.get(f"https://r.jina.ai/{url}", proxy=EGRESS_PROXY, timeout=30)
    resp.raise_for_status()
    return resp.text


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


if __name__ == "__main__":
    mcp.run()
