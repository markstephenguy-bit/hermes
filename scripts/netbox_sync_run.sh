#!/usr/bin/env bash
# Sources .env for SALT_PASS/NETBOX_TOKEN, then runs a netbox_*.py script.
# Usage: scripts/netbox_sync_run.sh netbox_sync.py --mode full
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
set -a
source .env
set +a

exec uv run --script "scripts/$1" "${@:2}"
