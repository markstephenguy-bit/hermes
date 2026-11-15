#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.27",
# ]
# ///
"""Ingest 6 infrastructure snapshot files + replacement fact into Cognee Cloud."""
import os
import sys
import time
from pathlib import Path
import httpx

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
DATASET = "infrastructure"

def remember(data: str, dataset_name: str = DATASET) -> dict:
    resp = httpx.post(
        f"{API_BASE_URL}/api/v1/remember",
        headers=HEADERS,
        data={"raw_data": data, "datasetName": dataset_name},
        timeout=60,
    )
    resp.raise_for_status()
    submitted = resp.json()
    dataset_id = submitted.get("dataset_id")
    if not dataset_id:
        return submitted
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        status_resp = httpx.get(
            f"{API_BASE_URL}/api/v1/datasets/status",
            headers=HEADERS,
            params={"dataset": [dataset_id]},
            timeout=30,
        )
        status_resp.raise_for_status()
        status = status_resp.json().get(dataset_id)
        if status in ("DATASET_PROCESSING_COMPLETED", "DATASET_PROCESSING_ERRORED"):
            return {**submitted, "final_status": status}
        time.sleep(3)
    return {**submitted, "final_status": "TIMED_OUT"}

def main():
    infra_dir = Path("/home/mark/projects/Hermes/data/infra_snapshots")
    files = sorted(infra_dir.glob("infra-2026-11-14-*.txt"))
    if not files:
        print("No snapshot files found in data/infra_snapshots", file=sys.stderr)
        sys.exit(1)

    print(f"Starting ingestion of {len(files)} files into Cognee Cloud dataset '{DATASET}'...", flush=True)
    t_start = time.time()

    for idx, path in enumerate(files, 1):
        content = path.read_text()
        print(f"[{idx}/{len(files)+1}] Ingesting {path.name} ({len(content)} chars)...", end="", flush=True)
        t0 = time.time()
        res = remember(content, DATASET)
        dur = time.time() - t0
        status = res.get("final_status")
        print(f" -> {status} ({dur:.1f}s)", flush=True)
        if status != "DATASET_PROCESSING_COMPLETED":
            print(f"Warning: {path.name} ended with status {status}: {res}", file=sys.stderr)

    replacement_fact = (
        'Cognee replaced Graphiti as the shared home-infrastructure knowledge store on 2026-11-15. '
        'Graphiti (FalkorDB-backed, on fileserver, MCP at 10.60.0.2:8766) was decommissioned. '
        'All six prior Graphiti infrastructure episodes were migrated into this Cognee "infrastructure" dataset. '
        'Any service-state details in those migrated snapshots are historical evidence from the time they were '
        'recorded, not a current status check -- verify live state before acting on them. Current MCP infrastructure '
        'memory queries for Codex, Claude Code, Antigravity, and Hermes should go through Cognee Cloud, not Graphiti.'
    )
    print(f"[{len(files)+1}/{len(files)+1}] Ingesting replacement fact ({len(replacement_fact)} chars)...", end="", flush=True)
    t0 = time.time()
    res = remember(replacement_fact, DATASET)
    dur = time.time() - t0
    status = res.get("final_status")
    print(f" -> {status} ({dur:.1f}s)", flush=True)

    print(f"Ingestion complete in {time.time() - t_start:.1f}s.", flush=True)

if __name__ == "__main__":
    main()
