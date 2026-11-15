#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fastmcp>=2.0",
#     "httpx>=0.27",
# ]
# ///
"""MCP server exposing Cognee Cloud (hosted, replaced the self-hosted fileserver
Cognee stack 2026-11-15) to Claude Code, Codex, Antigravity, and Hermes via plain
stdio - no OAuth dance per client. Cognee Cloud's hosted MCP endpoint
(https://mcp.aws.cognee.ai/mcp) requires OAuth 2.1 and does not accept static API
keys; this wrapper instead talks to Cognee Cloud's REST API directly, which does
accept a static X-Api-Key/X-Tenant-Id pair, and re-exposes it as a normal
unauthenticated local MCP server.

Credentials read from ~/.config/cognee-cloud/credentials.env (0600, not in any
git repo) unless overridden by environment variables of the same names.
"""
import os
import time
from pathlib import Path

import httpx
from fastmcp import FastMCP

CREDS_FILE = Path.home() / ".config" / "cognee-cloud" / "credentials.env"
if CREDS_FILE.exists():
    for line in CREDS_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

API_BASE_URL = os.environ["COGNEE_CLOUD_API_BASE_URL"]
API_KEY = os.environ["COGNEE_CLOUD_API_KEY"]
TENANT_ID = os.environ["COGNEE_CLOUD_TENANT_ID"]

HEADERS = {"X-Api-Key": API_KEY, "X-Tenant-Id": TENANT_ID}
DEFAULT_DATASET = os.environ.get("COGNEE_DEFAULT_DATASET", "main_dataset")

mcp = FastMCP(name="cognee-cloud")


@mcp.tool
def remember(data: str, dataset_name: str = DEFAULT_DATASET, background: bool = False) -> dict:
    """Store text in Cognee Cloud's knowledge graph (dataset created if it doesn't exist).
    Blocks until graph extraction finishes unless background=True, which returns immediately
    with a dataset_id/status and leaves the pipeline running. Use ingestion_status
    with the returned dataset_id to check completion."""
    resp = httpx.post(
        f"{API_BASE_URL}/api/v1/remember",
        headers=HEADERS,
        data={"raw_data": data, "datasetName": dataset_name,
              "run_in_background": str(background).lower()},
        timeout=60 if background else 300,
    )
    resp.raise_for_status()
    submitted = resp.json()
    if background:
        return submitted
    dataset_id = submitted.get("dataset_id")
    if not dataset_id:
        return submitted
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        status = ingestion_status(dataset_id).get("status")
        if status in ("DATASET_PROCESSING_COMPLETED", "DATASET_PROCESSING_ERRORED"):
            return {**submitted, "final_status": status}
        time.sleep(3)
    return {**submitted, "final_status": "TIMED_OUT_WAITING"}


@mcp.tool
def ingestion_status(dataset_id: str) -> dict:
    """Check whether a background remember call has finished processing.

    Pass the dataset_id returned by remember(background=True).
    """
    resp = httpx.get(
        f"{API_BASE_URL}/api/v1/datasets/status",
        headers=HEADERS,
        params={"dataset": [dataset_id]},
        timeout=30,
    )
    resp.raise_for_status()
    return {"dataset_id": dataset_id, "status": resp.json().get(dataset_id)}


@mcp.tool
def recall(query: str, datasets: list[str] | None = None, search_type: str | None = None,
           top_k: int = 10) -> dict:
    """Search Cognee Cloud's knowledge graph. Omit datasets to search everything readable;
    search_type pins a strategy (HYBRID_COMPLETION, GRAPH_COMPLETION, RAG_COMPLETION, CHUNKS, ...),
    omit to let Cognee auto-route."""
    payload: dict = {"query": query, "topK": top_k}
    if datasets:
        payload["datasets"] = datasets
    if search_type:
        payload["searchType"] = search_type
    resp = httpx.post(
        f"{API_BASE_URL}/api/v1/recall",
        headers=HEADERS,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    body = resp.json()
    return body if isinstance(body, dict) else {"result": body}


@mcp.tool
def list_datasets() -> dict:
    """List datasets in this Cognee Cloud workspace."""
    resp = httpx.get(f"{API_BASE_URL}/api/v1/datasets/", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    return {"datasets": body} if isinstance(body, list) else body


if __name__ == "__main__":
    mcp.run()
