#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fastmcp>=2.0",
#     "httpx>=0.27",
# ]
# ///
"""MCP server exposing Hindsight (migrated 2026-10-22 from hermes-vps to a
Docker deployment on w_workstation, port 8888, LAN-reachable at
192.168.40.100) to Claude Code, Codex, and any other MCP-capable AI tool.
Runs locally wherever this script is invoked and talks to Hindsight over
plain HTTP - no SSH hop needed now that Hindsight isn't loopback-bound.

This is the successor to the fileserver Postgres/PostgREST catalog for
Hermes's own memory: new facts/decisions go here, not to the old catalog.
"""
import os

import httpx
from fastmcp import FastMCP

HINDSIGHT_URL = os.environ.get("HINDSIGHT_URL", "http://192.168.40.100:8888")
DEFAULT_BANK = os.environ.get("HINDSIGHT_BANK", "hermes")

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
    mcp.run()
