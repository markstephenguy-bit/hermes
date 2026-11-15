#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.27",
# ]
# ///
"""Export all memories from Hindsight's hermes bank into JSON files."""
import json
import os
from pathlib import Path
import httpx

HINDSIGHT_URL = os.environ.get("HINDSIGHT_URL", "http://192.168.40.100:8888/hindsight")
BANK_ID = os.environ.get("HINDSIGHT_BANK", "hermes")
OUT_DIR = Path("/home/mark/projects/Hermes/data/hindsight_dump")
PAGE_SIZE = 500

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    offset = 0
    total = None
    all_items = []
    page_num = 0

    print(f"Exporting memories from Hindsight ({HINDSIGHT_URL}, bank={BANK_ID})...", flush=True)

    with httpx.Client(timeout=30) as client:
        while True:
            url = f"{HINDSIGHT_URL}/v1/default/banks/{BANK_ID}/memories/list"
            resp = client.get(url, params={"limit": PAGE_SIZE, "offset": offset})
            resp.raise_for_status()
            data = resp.json()

            items = data.get("items", [])
            total = data.get("total", total)
            if not items:
                break

            out_file = OUT_DIR / f"page_{offset}.json"
            out_file.write_text(json.dumps(data, indent=2))
            all_items.extend(items)
            page_num += 1
            print(f"Page {page_num}: offset={offset}, fetched {len(items)} items. Total so far: {len(all_items)}/{total}", flush=True)

            offset += len(items)
            if total is not None and offset >= total:
                break

    print(f"Export complete. Saved {len(all_items)} memories across {page_num} pages in {OUT_DIR}.", flush=True)

if __name__ == "__main__":
    main()
