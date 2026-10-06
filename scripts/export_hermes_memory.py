#!/usr/bin/env python3
"""Back up what Hermes itself remembers (SOUL.md + memories/*.md on hermes-vps)
into the git repo, parallel to export_catalog_memory.py. hermes-vps is a
single Vultr box with no other backup of these files - this is a dead backup
only, never read FROM while the box is reachable.
"""
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SSH_KEY = str(Path.home() / ".ssh" / "id_ed25519")
HOST = "root@207.148.2.224"
REMOTE_FILES = [
    "/home/hermes/.hermes/SOUL.md",
    "/home/hermes/.hermes/memories/USER.md",
    "/home/hermes/.hermes/memories/MEMORY.md",
]
OUT_DIR = Path("memory/hermes-vps-backup")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fetched = []
    for remote_path in REMOTE_FILES:
        name = remote_path.rsplit("/", 1)[-1]
        result = subprocess.run(
            ["ssh", "-i", SSH_KEY, "-o", "BatchMode=yes", HOST, "cat", remote_path],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"skip {name}: not present on hermes-vps yet")
            continue
        (OUT_DIR / name).write_text(result.stdout)
        fetched.append(name)

    manifest = OUT_DIR / "MANIFEST.txt"
    manifest.write_text(
        f"Exported {datetime.now(timezone.utc).isoformat()}\n"
        f"Source: hermes-vps (207.148.2.224), dead backup only - never read FROM while the box is reachable.\n"
        f"Files: {', '.join(fetched) if fetched else '(none present yet)'}\n"
    )
    print(f"Backed up {len(fetched)} file(s): {', '.join(fetched)}")


if __name__ == "__main__":
    main()
