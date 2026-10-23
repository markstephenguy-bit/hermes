#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fastmcp>=2.0",
#     "httpx>=0.27",
# ]
# ///
"""HTTP-transport sidecar exposing Hindsight as an MCP server for Hermes Agent's
own `mcp_servers` config (Hermes only speaks stdio/HTTP MCP, not Hindsight's raw
REST API). Same tool surface as hindsight_mcp.py (used by Claude Code/Codex over
stdio) but served over streamable-HTTP so Hermes's config.yaml can point a plain
`url:` entry at it. Runs as its own container on w_workstation, on hindsight-net,
next to the hindsight/hindsight-postgres containers.
"""
import os

import httpx
from fastmcp import FastMCP

HINDSIGHT_URL = os.environ.get("HINDSIGHT_URL", "http://hindsight:8888")
DEFAULT_BANK = os.environ.get("HINDSIGHT_BANK", "hermes")
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8891"))

mcp = FastMCP(name="hindsight")


@mcp.tool
def retain(content: str, context: str = "", document_id: str = "", metadata: dict | None = None,
           bank_id: str = DEFAULT_BANK) -> dict:
    """Store a new fact/decision/observation in Hindsight. Use a distinct document_id per
    source event so related items group together; metadata values must be strings."""
    item: dict = {"content": content}
    if context:
        item["context"] = context
    if document_id:
        item["document_id"] = document_id
    if metadata:
        item["metadata"] = {k: str(v) for k, v in metadata.items()}
    resp = httpx.post(
        f"{HINDSIGHT_URL}/v1/default/banks/{bank_id}/memories",
        json={"async": False, "items": [item]},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def recall(query: str, bank_id: str = DEFAULT_BANK, budget: str = "mid", max_tokens: int = 4096,
           tags: list[str] | None = None) -> dict:
    """Semantic recall over Hindsight's memory for a bank. budget: low/mid/high controls
    how much is searched; tags optionally filters to memories carrying all given tags."""
    payload: dict = {"query": query, "budget": budget, "max_tokens": max_tokens}
    if tags:
        payload["tags"] = tags
    resp = httpx.post(
        f"{HINDSIGHT_URL}/v1/default/banks/{bank_id}/memories/recall",
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def reflect(query: str, bank_id: str = DEFAULT_BANK, budget: str = "low", max_tokens: int = 4096) -> dict:
    """Ask Hindsight a question; it searches its own memory and returns a synthesized answer
    (not just raw matches) - use this over recall when you want a conclusion, not a fact list."""
    resp = httpx.post(
        f"{HINDSIGHT_URL}/v1/default/banks/{bank_id}/reflect",
        json={"query": query, "budget": budget, "max_tokens": max_tokens},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def list_memories(bank_id: str = DEFAULT_BANK, limit: int = 20) -> dict:
    """List recent memory units in a bank, newest first."""
    resp = httpx.get(
        f"{HINDSIGHT_URL}/v1/default/banks/{bank_id}/memories/list",
        params={"limit": limit},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def get_entities(bank_id: str = DEFAULT_BANK, limit: int = 50) -> dict:
    """List entities Hindsight has extracted/tracked for a bank (people, systems, projects, etc.)."""
    resp = httpx.get(
        f"{HINDSIGHT_URL}/v1/default/banks/{bank_id}/entities",
        params={"limit": limit},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def list_banks() -> dict:
    """List every memory bank Hindsight knows about."""
    resp = httpx.get(f"{HINDSIGHT_URL}/v1/default/banks", timeout=10)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    mcp.run(transport="http", host=MCP_HOST, port=MCP_PORT)
