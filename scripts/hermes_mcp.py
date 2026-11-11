#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fastmcp>=2.0",
#     "httpx>=0.27",
# ]
# ///
"""MCP server exposing Hermes Agent's own REST API (the `api_server` platform,
port 8642 by default - NOT the port-9119 dashboard, which is a separate
basic-auth web UI with no REST surface) to Claude Code, Codex, and any other
MCP-capable AI tool, so an outside harness can call into a running Hermes
instance instead of only the other way around.

Same shape as scripts/hindsight_mcp.py: a thin wrapper over an existing HTTP
API, no new architecture. Reuses the exact env var names already established
in testing/README.md and testing/stress_test_*.py (HERMES_BASE_URL,
HERMES_API_KEY, HERMES_MODEL) rather than inventing new ones, since those
scripts are the only in-repo code that has actually exercised this API live.

Verified-real endpoint (used by every stress_test_*.py script against a real
Hermes instance): POST {base}/v1/responses, bearer auth, body
{model, input, store, conversation, model_options}. `hermes_chat` below
mirrors that exact shape.

The remaining tools (/v1/capabilities, /v1/skills, /v1/toolsets, /api/sessions,
/api/jobs, /v1/runs) are named in Hermes's documented API surface but have
NOT been live-verified from this repo the way /v1/responses has - BACKLOG.md
notes /v1/skills has had a live TypeError bug before. They're implemented as
plain GET list/get calls (low-risk) plus a generic `hermes_api_request` escape
hatch for anything with a POST/PATCH body shape that hasn't been confirmed
live (run steer/stop/approve, job create/cancel, session fork/chat/stream).
Firm up the specific wrappers once the Install session has a live api_server
to verify shapes against, rather than guessing payload keys here.

Where this actually runs, and what HERMES_BASE_URL/HERMES_API_KEY point at
(hermes-vps direct, WireGuard mesh, or folded into the shared
mcp.markstephenguy.com gateway container) is a deployment decision for
Infra/Ops, not baked in here - same as HINDSIGHT_URL in hindsight_mcp.py.
"""
import os

import httpx
from fastmcp import FastMCP

HERMES_BASE_URL = os.environ.get("HERMES_BASE_URL", "http://localhost:8642").rstrip("/")
HERMES_API_KEY = os.environ.get("HERMES_API_KEY", "")
HERMES_MODEL = os.environ.get("HERMES_MODEL", "hermes")

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
    mcp.run()
