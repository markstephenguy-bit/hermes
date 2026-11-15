#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.27",
# ]
# ///
"""Migrate full Hindsight export into Cognee Cloud dataset 'hindsight_migration'."""
import glob
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
PROGRESS_FILE = Path("/home/mark/projects/Hermes/data/hindsight_migration_progress.json")
LOG_FILE = Path("/home/mark/projects/Hermes/data/hindsight_migration.log")

MAX_PENDING_WINDOW = 10  # keep up to 10 items in flight in Cognee Cloud


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


def get_dataset_info(client: httpx.Client, dataset_id: str | None = None) -> tuple[str | None, int, int]:
    """Returns (dataset_id, completed_count, pending_count)."""
    if not dataset_id:
        resp = client.get(f"{API_BASE_URL}/api/v1/datasets/", headers=HEADERS, timeout=30)
        resp.raise_for_status()
        datasets = resp.json()
        for ds in datasets:
            if ds.get("name") == DATASET:
                dataset_id = ds.get("id")
                break
    if not dataset_id:
        return None, 0, 0

    st_resp = client.get(
        f"{API_BASE_URL}/api/v1/datasets/{dataset_id}/processing-status",
        headers=HEADERS,
        timeout=30,
    )
    if st_resp.status_code == 200:
        data = st_resp.json()
        return dataset_id, data.get("completed", 0), data.get("pending", 0)
    return dataset_id, 0, 0


def submit_remember(client: httpx.Client, blob: str) -> dict:
    for attempt in range(5):
        try:
            resp = client.post(
                f"{API_BASE_URL}/api/v1/remember",
                headers=HEADERS,
                data={"raw_data": blob, "datasetName": DATASET},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == 4:
                raise
            backoff = (attempt + 1) * 3
            log(f"HTTP error ({exc}), retrying in {backoff}s...")
            time.sleep(backoff)


def main():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log("=== Starting Hindsight -> Cognee Cloud Migration ===")

    # 1. Load exported facts
    items = []
    files = sorted(glob.glob(str(DUMP_DIR / "page_*.json")))
    if not files:
        log(f"Error: no dump files found in {DUMP_DIR}")
        sys.exit(1)
    for f in files:
        with open(f) as fp:
            items.extend(json.load(fp).get("items", []))
    log(f"Loaded {len(items)} total facts from {len(files)} dump pages.")

    # 2. Form batches (by document_id, and 50-item chunks for no-doc facts)
    by_doc = defaultdict(list)
    no_doc = []
    for m in items:
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
    log(f"Prepared {total_batches} batches ({len(by_doc)} document groups, {len(chunks)} ungrouped chunks).")

    # 3. Load progress if exists
    progress = {"submitted": 0, "completed_batches": []}
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE) as fp:
                progress = json.load(fp)
            log(f"Resuming from progress file: {progress.get('submitted', 0)}/{total_batches} already submitted.")
        except Exception as e:
            log(f"Could not read progress file ({e}), starting fresh.")

    submitted_count = progress.get("submitted", 0)

    with httpx.Client(timeout=30) as client:
        dataset_id, completed_items, pending_items = get_dataset_info(client)
        if dataset_id:
            log(f"Found existing dataset {DATASET} ({dataset_id}): {completed_items} completed, {pending_items} pending.")
        else:
            log(f"Dataset {DATASET} will be created with first batch.")

        t_start = time.time()

        for idx in range(submitted_count, total_batches):
            label, date_hint, members = batches[idx]
            blob = build_blob(label, date_hint, members)

            # Check pending window throttle
            if dataset_id:
                while True:
                    _, comp, pend = get_dataset_info(client, dataset_id)
                    if pend < MAX_PENDING_WINDOW:
                        break
                    time.sleep(3)

            # Submit batch
            t0 = time.time()
            sub = submit_remember(client, blob)
            if not dataset_id:
                dataset_id = sub.get("dataset_id")
            dur = time.time() - t0

            submitted_count += 1
            progress["submitted"] = submitted_count
            progress["completed_batches"].append(label)

            # Update progress file every batch
            with open(PROGRESS_FILE, "w") as fp:
                json.dump(progress, fp)

            if submitted_count % 10 == 0 or submitted_count == total_batches:
                _, comp, pend = get_dataset_info(client, dataset_id)
                log(f"[{submitted_count}/{total_batches}] Submitting '{label}' ({len(members)} facts, {len(blob)} chars) | Cloud: {comp} done, {pend} pending")
            else:
                log(f"[{submitted_count}/{total_batches}] Submitted '{label}' ({len(members)} facts, {dur:.2f}s)")

            time.sleep(0.5)

        log("All batches submitted! Waiting for final cloud processing completion...")

        while True:
            _, comp, pend = get_dataset_info(client, dataset_id)
            log(f"Processing status: {comp}/{total_batches} completed, {pend} pending...")
            if pend == 0 and comp >= total_batches:
                log("All items completed processing in Cognee Cloud!")
                break
            time.sleep(5)

        total_dur = time.time() - t_start
        log(f"=== Migration complete in {total_dur/60:.1f} minutes ===")


if __name__ == "__main__":
    main()
