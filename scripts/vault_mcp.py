#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fastmcp>=2.0",
#     "httpx>=0.27",
# ]
# ///
"""MCP server exposing the home-lab secrets vault (Postgres + pgcrypto, via
PostgREST) to Claude Code, Codex, and Hermes alike - one shared passcode
unlocks any stored secret, for use against any connected system.
"""
import os

import httpx
from fastmcp import FastMCP

CATALOG_URL = os.environ.get("CATALOG_URL", "http://192.168.40.2:3003")

mcp = FastMCP(name="vault")


@mcp.tool
def list_secrets() -> list[dict]:
    """List every stored secret's name and metadata (host, purpose, username) - no passcode needed, values are never included."""
    resp = httpx.get(f"{CATALOG_URL}/secrets", params={"select": "name,attributes"}, timeout=10)
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def get_secret(name: str, passcode: str) -> str:
    """Decrypt and return a stored secret's plaintext value, given its name and the vault passcode."""
    resp = httpx.post(
        f"{CATALOG_URL}/rpc/secret_get",
        json={"p_name": name, "p_passphrase": passcode},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def set_secret(name: str, plaintext: str, passcode: str, attributes: dict | None = None) -> str:
    """Store or update a secret's value, given the vault passcode. Upserts by name."""
    resp = httpx.post(
        f"{CATALOG_URL}/rpc/secret_set",
        json={
            "p_name": name,
            "p_plaintext": plaintext,
            "p_passphrase": passcode,
            "p_attributes": attributes or {},
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.text


if __name__ == "__main__":
    mcp.run()
