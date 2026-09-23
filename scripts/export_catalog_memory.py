#!/usr/bin/env python3
"""Back up this project's catalog memory (entities tagged 'hermes' + their
relations) into the git repo, so it survives even if `server` is down or the
catalog DB is lost. The catalog stays the live/queryable copy; this file is
a dead backup only - never read FROM this file when the catalog is reachable.
"""
import json
import urllib.request
from datetime import datetime, timezone

CATALOG = "http://192.168.40.250:3003"


def get(path):
    with urllib.request.urlopen(f"{CATALOG}{path}") as r:
        return json.load(r)


def main():
    entities = get("/entities?tags=cs.%7Bhermes%7D")
    for e in entities:
        e.pop("embedding", None)
        e.pop("search", None)

    keys = {e["key"] for e in entities}
    all_relations = get("/relations")
    relations = [
        r for r in all_relations
        if r.get("subject_key") in keys or r.get("object_key") in keys
    ]

    out = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source": f"{CATALOG} (Postgres+PostgREST on `server`, live copy is authoritative)",
        "entities": entities,
        "relations": relations,
    }

    with open("memory/catalog-export.json", "w") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Exported {len(entities)} entities, {len(relations)} relations.")


if __name__ == "__main__":
    main()
