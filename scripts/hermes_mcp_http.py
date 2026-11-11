#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fastmcp>=2.0",
#     "httpx>=0.27",
# ]
# ///
"""HTTP-transport sidecar exposing Hermes Agent's REST API as an MCP server -
same tool surface as hermes_mcp.py (used over stdio by Claude Code/Codex) but
served over streamable-HTTP, for Hermes's own `mcp_servers:` config or for
registration into a shared gateway container (e.g. mcp.markstephenguy.com)
the way hindsight_mcp_http.py already is. See hermes_mcp.py's module docstring
for the full rationale and the endpoints that are live-verified vs. not.

HERMES_BASE_URL/HERMES_API_KEY must point at wherever this instance's
api_server (port 8642 by default) is actually reachable from this container's
network - direct LAN/WireGuard IP, a Docker service name on a shared compose
network, or the public host - a deployment choice for whoever stands this
container up, not decided here.
"""
import os

import httpx
from fastmcp import FastMCP

HERMES_BASE_URL = os.environ.get("HERMES_BASE_URL", "http://localhost:8642").rstrip("/")
HERMES_API_KEY = os.environ.get("HERMES_API_KEY", "")
HERMES_MODEL = os.environ.get("HERMES_MODEL", "hermes")
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8892"))

mcp = FastMCP(name="hermes")


def _headers() -> dict:
    headers = {}
    if HERMES_API_KEY:
        headers["Authorization"] = f"Bearer {HERMES_API_KEY}"
    return headers


@mcp.tool
def hermes_chat(input: str, conversation: str | None = None, model: str | None = None,
                 max_tokens: int | None = None, reasoning: bool = False, store: bool = True) -> dict:
    """Send a message to Hermes Agent via its /v1/responses endpoint and get its reply.
    conversation is a free-form thread id - reuse the same one across calls to continue a
    conversation, omit it to start a fresh one. reasoning enables Hermes's own reasoning mode."""
    payload: dict = {
        "model": model or HERMES_MODEL,
        "input": input,
        "store": store,
        "model_options": {"reasoning": {"enabled": reasoning}},
    }
    if conversation:
        payload["conversation"] = conversation
    if max_tokens:
        payload["max_tokens"] = max_tokens
    resp = httpx.post(f"{HERMES_BASE_URL}/v1/responses", headers=_headers(), json=payload, timeout=180)
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def hermes_capabilities() -> dict:
    """List what this Hermes instance's api_server advertises as enabled (tools, platforms, limits)."""
    resp = httpx.get(f"{HERMES_BASE_URL}/v1/capabilities", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def hermes_skills_list() -> dict:
    """List skills installed on this Hermes instance."""
    resp = httpx.get(f"{HERMES_BASE_URL}/v1/skills", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def hermes_toolsets_list() -> dict:
    """List toolsets (grouped tool bundles) available on this Hermes instance."""
    resp = httpx.get(f"{HERMES_BASE_URL}/v1/toolsets", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def hermes_sessions_list(limit: int = 20) -> dict:
    """List this Hermes instance's recent sessions."""
    resp = httpx.get(f"{HERMES_BASE_URL}/api/sessions", headers=_headers(), params={"limit": limit}, timeout=15)
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def hermes_session_get(session_id: str) -> dict:
    """Get a single Hermes session by id."""
    resp = httpx.get(f"{HERMES_BASE_URL}/api/sessions/{session_id}", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def hermes_jobs_list() -> dict:
    """List scheduled/background jobs (e.g. cron jobs) on this Hermes instance."""
    resp = httpx.get(f"{HERMES_BASE_URL}/api/jobs", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def hermes_job_get(job_id: str) -> dict:
    """Get a single Hermes job by id."""
    resp = httpx.get(f"{HERMES_BASE_URL}/api/jobs/{job_id}", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def hermes_runs_list(limit: int = 20) -> dict:
    """List this Hermes instance's recent agent runs."""
    resp = httpx.get(f"{HERMES_BASE_URL}/v1/runs", headers=_headers(), params={"limit": limit}, timeout=15)
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def hermes_run_get(run_id: str) -> dict:
    """Get a single Hermes run by id."""
    resp = httpx.get(f"{HERMES_BASE_URL}/v1/runs/{run_id}", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def hermes_run_events(run_id: str) -> dict:
    """Get the event log for a single Hermes run."""
    resp = httpx.get(f"{HERMES_BASE_URL}/v1/runs/{run_id}/events", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def hermes_api_request(method: str, path: str, json_body: dict | None = None) -> dict:
    """Escape hatch: call any Hermes api_server endpoint directly (method is GET/POST/PATCH/
    DELETE/PUT, path is relative like "/v1/runs/123/steer"). Use this for actions not covered
    by a dedicated tool above (run steer/stop/approve, job create/cancel, session fork/chat/
    stream) whose exact payload shape hasn't been verified live from this wrapper yet."""
    resp = httpx.request(
        method.upper(), f"{HERMES_BASE_URL}{path}", headers=_headers(), json=json_body, timeout=60,
    )
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception:
        return {"status_code": resp.status_code, "text": resp.text}


if __name__ == "__main__":
    mcp.run(transport="http", host=MCP_HOST, port=MCP_PORT)
