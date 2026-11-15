#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.27",
# ]
# ///
"""Submit remaining Hindsight batches to Cognee Cloud with verified addition."""
import glob
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
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

DUMP_DIR = Path("/home/mark/projects/Hermes/data/hindsight_dump")
LOG_FILE = Path("/home/mark/projects/Hermes/data/hindsight_migration.log")


def log(msg: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def fact_line(m: dict) -> str:
    line = f"- {m.get('text', '')}"
    if m.get("context"):
        line += f" (Context: {m['context']})"
    if m.get("metadata"):
        md = {k: v for k, v in m["metadata"].items() if v}
        if md:
            line += f" [metadata: {json.dumps(md)}]"
    return line


def build_blob(label: str, date_hint: str, members: list[dict]) -> str:
    header = (
        f"Migrated from Hindsight (bank=hermes, {label}, originally recorded around {date_hint}). "
        "Cognee replaced Graphiti as the shared knowledge store on 2026-11-15, and Cognee Cloud "
        "replaced self-hosted Cognee. This content reflects Hindsight's memory at migration time (2026-11-15) "
        "and may describe superseded state; verify anything time-sensitive against live systems.\n\n"
    )
    return header + "\n".join(fact_line(m) for m in members)


def get_cloud_dataset_id(client: httpx.Client) -> str:
    r = client.get(f"{API_BASE_URL}/api/v1/datasets/", headers=HEADERS, timeout=30)
    r.raise_for_status()
    for ds in r.json():
        if ds.get("name") == DATASET:
            return ds.get("id")
    raise RuntimeError(f"Dataset {DATASET} not found")


def get_cloud_hashes(client: httpx.Client, ds_id: str) -> set[str]:
    r = client.get(f"{API_BASE_URL}/api/v1/datasets/{ds_id}/data?limit=500", headers=HEADERS, timeout=60)
    r.raise_for_status()
    return {it.get("contentHash") for it in r.json() if it.get("contentHash")}


def get_processing_status(client: httpx.Client, ds_id: str) -> tuple[int, int, int]:
    r = client.get(f"{API_BASE_URL}/api/v1/datasets/{ds_id}/processing-status", headers=HEADERS, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data.get("total", 0), data.get("completed", 0), data.get("pending", 0)


def main():
    log("=== Resuming Remaining Batches Migration ===")

    # 1. Load exported facts & form batches
    dump_items = []
    for f in sorted(glob.glob(str(DUMP_DIR / "page_*.json"))):
        with open(f) as fp:
            dump_items.extend(json.load(fp).get("items", []))

    by_doc = defaultdict(list)
    no_doc = []
    for m in dump_items:
        if m.get("document_id"):
            by_doc[m["document_id"]].append(m)
        else:
            no_doc.append(m)

    no_doc.sort(key=lambda m: m.get("date") or "")
    CHUNK = 50
    chunks = [no_doc[i:i + CHUNK] for i in range(0, len(no_doc), CHUNK)]

    batches = []
    for doc_id, members in by_doc.items():
        date_hint = members[0].get("date", "?")
        batches.append((f"document_id={doc_id}", date_hint, members))
    for i, members in enumerate(chunks):
        d0 = members[0].get("date", "?")
        d1 = members[-1].get("date", "?")
        batches.append((f"ungrouped_chunk_{i}", f"{d0} to {d1}", members))

    total_batches = len(batches)

    with httpx.Client(timeout=30) as client:
        ds_id = get_cloud_dataset_id(client)
        cloud_hashes = get_cloud_hashes(client, ds_id)
        tot, comp, pend = get_processing_status(client, ds_id)
        log(f"Dataset {DATASET} ({ds_id}): total={tot}, completed={comp}, pending={pend}")

        missing = []
        for idx, (label, date_hint, members) in enumerate(batches):
            blob = build_blob(label, date_hint, members)
            h = hashlib.md5(blob.encode()).hexdigest()
            if h not in cloud_hashes:
                missing.append((idx, label, date_hint, members, blob, h))

        log(f"Found {len(missing)} batches missing from Cloud out of {total_batches}.")
        if not missing:
            log("All batches already present in Cloud!")
            return

        t_start = time.time()
        for count, (idx, label, date_hint, members, blob, blob_hash) in enumerate(missing, 1):
            # Throttle: ensure pending < 5 before submitting new item
            while True:
                _, comp, pend = get_processing_status(client, ds_id)
                if pend < 5:
                    break
                time.sleep(3)

            # Submit batch with retry until hash is confirmed in Cloud
            for attempt in range(5):
                t0 = time.time()
                resp = client.post(
                    f"{API_BASE_URL}/api/v1/remember",
                    headers=HEADERS,
                    data={"raw_data": blob, "datasetName": DATASET},
                    timeout=60,
                )
                dur = time.time() - t0
                if resp.status_code == 200:
                    time.sleep(1.0)
                    cloud_hashes = get_cloud_hashes(client, ds_id)
                    if blob_hash in cloud_hashes:
                        log(f"[{count}/{len(missing)}] (Batch #{idx+1} '{label}') added successfully ({len(members)} facts, {dur:.2f}s) | Cloud total: {len(cloud_hashes)}/272")
                        break
                    else:
                        log(f"Batch #{idx+1} '{label}' returned 200 but hash not yet in Cloud. Waiting 3s (attempt {attempt+1}/5)...")
                        time.sleep(3)
                else:
                    log(f"Batch #{idx+1} '{label}' HTTP {resp.status_code}: {resp.text}")
                    time.sleep(3)

        log("All missing batches submitted and verified present in Cloud! Waiting for final processing completion...")

        while True:
            tot, comp, pend = get_processing_status(client, ds_id)
            log(f"Final processing: {comp}/{tot} completed, {pend} pending...")
            if pend == 0 and comp >= total_batches:
                log(f"All {tot} items completed processing in Cognee Cloud!")
                break
            time.sleep(5)

        total_dur = time.time() - t_start
        log(f"=== Remaining batches migration complete in {total_dur/60:.1f} minutes ===")


if __name__ == "__main__":
    main()
