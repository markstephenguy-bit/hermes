#!/usr/bin/env python3
"""MCP server exposing the home-lab catalog (Postgres + PostgREST) as tools for Hermes.

Deliberately excludes /secrets and /rpc/secret_* - credential access stays
out of general-purpose tool calls. Deliberately excludes /rpc/search_similar
too, since it requires a pre-computed 768-float embedding that nothing in
this process can generate; add it back once an embedding provider is wired in.
"""
import os

import httpx
from fastmcp import FastMCP

CATALOG_URL = os.environ.get("CATALOG_URL", "http://192.168.40.250:3003")

mcp = FastMCP(name="catalog")


@mcp.tool
def get_entities(tag: str = "", search: str = "", limit: int = 20) -> list[dict]:
    """List catalog entities, optionally filtered by tag or full-text search term."""
    params: dict[str, str] = {"limit": str(limit), "order": "updated_at.desc"}
    if tag:
        params["tags"] = f"cs.{{{tag}}}"
    if search:
        params["search"] = f"fts.{search}"
    resp = httpx.get(f"{CATALOG_URL}/entities", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def get_hosts() -> list[dict]:
    """List all known hosts on the home network."""
    resp = httpx.get(f"{CATALOG_URL}/hosts", timeout=10)
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def get_services() -> list[dict]:
    """List all known services running on home network hosts."""
    resp = httpx.get(f"{CATALOG_URL}/services", timeout=10)
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def add_entity(
    type: str,
    key: str,
    name: str,
    body: str,
    tags: list[str],
    attributes: dict | None = None,
) -> dict:
    """Add a new entity to the catalog's persistent memory (decision, log-entry, gap, risk, etc.)."""
    payload = {
        "type": type,
        "key": key,
        "name": name,
        "body": body,
        "tags": tags,
        "attributes": attributes or {},
    }
    resp = httpx.post(
        f"{CATALOG_URL}/entities",
        json=payload,
        headers={"Prefer": "return=representation"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def add_relation(
    subject_type: str, subject_key: str, predicate: str, object_type: str, object_key: str
) -> dict:
    """Link two catalog entities/hosts together, e.g. subject 'entity' relates to object 'host'."""
    payload = {
        "subject_type": subject_type,
        "subject_key": subject_key,
        "predicate": predicate,
        "object_type": object_type,
        "object_key": object_key,
    }
    resp = httpx.post(
        f"{CATALOG_URL}/relations",
        json=payload,
        headers={"Prefer": "return=representation"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def graph_recall(seed_type: str, seed_key: str, max_hops: int = 2, decay: float = 0.6) -> list[dict]:
    """Hop-limited graph traversal from one seed node via relations; relevance decays per hop."""
    payload = {"seed_type": seed_type, "seed_key": seed_key, "max_hops": max_hops, "decay": decay}
    resp = httpx.post(f"{CATALOG_URL}/rpc/graph_recall", json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    mcp.run()
