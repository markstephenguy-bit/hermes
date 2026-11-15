#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.27",
# ]
# ///
"""Wait for hindsight_migration dataset processing to complete in Cognee Cloud."""
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
DATASET = "hindsight_migration"
LOG_FILE = Path("/home/mark/projects/Hermes/data/hindsight_migration.log")


def log(msg: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def main():
    log("=== Waiting for hindsight_migration pipeline completion ===")
    with httpx.Client(timeout=60) as client:
        # Find dataset ID
        r = client.get(f"{API_BASE_URL}/api/v1/datasets/", headers=HEADERS)
        r.raise_for_status()
        ds_id = None
        for ds in r.json():
            if ds.get("name") == DATASET:
                ds_id = ds.get("id")
                break
        if not ds_id:
            log(f"Error: Dataset {DATASET} not found")
            sys.exit(1)

        t_start = time.time()
        while True:
            try:
                r_status = client.get(
                    f"{API_BASE_URL}/api/v1/datasets/{ds_id}/processing-status",
                    headers=HEADERS,
                )
                if r_status.status_code == 200:
                    data = r_status.json()
                    tot = data.get("total", 0)
                    comp = data.get("completed", 0)
                    pend = data.get("pending", 0)
                    elapsed = time.time() - t_start
                    log(f"[{elapsed:.0f}s elapsed] Progress: {comp}/{tot} completed, {pend} pending")
                    if pend == 0 and comp >= tot and tot > 0:
                        log("All items completed processing in Cognee Cloud!")
                        break
            except Exception as e:
                log(f"Transient error polling status: {e}")

            time.sleep(15)

        # Run verification recall
        log("Testing recall against hindsight_migration...")
        recall_resp = client.post(
            f"{API_BASE_URL}/api/v1/recall",
            headers=HEADERS,
            json={"query": "What is the architecture and history of Hermes memory?", "datasets": [DATASET]},
            timeout=60,
        )
        if recall_resp.status_code == 200:
            log(f"Verification recall successful: {recall_resp.text[:500]}")
        else:
            log(f"Verification recall HTTP {recall_resp.status_code}: {recall_resp.text}")


if __name__ == "__main__":
    main()
