#!/usr/bin/env python3
"""Dedicated Salt API client for Hermes infrastructure management.
Executes commands against the Salt Master REST API at http://192.168.40.2:8000
using vaulted hermes-infra credentials over direct HTTP (zero SSH involvement).
"""
import os
import subprocess
import sys
import json
import httpx

SALT_URL = "http://192.168.40.2:8000"
VAULT_ITEM_NAME = "salt-hermes-infra"
BW_SESSION_ENV_FILE = os.path.expanduser("~/.claude/mcp_servers/bitwarden/bw_session.env")


def get_salt_password() -> str:
    """Retrieve the salt-hermes-infra password from Vaultwarden via the bw CLI.

    Vaultwarden is the sole secrets source (see Hermes's CLAUDE.md). This
    reuses the session token set up by scripts/onboard_bitwarden_mcp.sh
    (BW_SESSION_ENV_FILE) so no password/session handling happens here - if
    that session has gone stale, re-run the onboarding script.
    """
    env = os.environ.copy()
    if "BW_SESSION" not in env and os.path.exists(BW_SESSION_ENV_FILE):
        with open(BW_SESSION_ENV_FILE) as f:
            for line in f:
                if line.startswith("export BW_SESSION="):
                    env["BW_SESSION"] = line.split("=", 1)[1].strip()
                    break

    result = subprocess.run(
        ["bw", "get", "password", VAULT_ITEM_NAME],
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"Failed to fetch '{VAULT_ITEM_NAME}' from Vaultwarden: {result.stderr.strip()}\n"
            f"Run scripts/onboard_bitwarden_mcp.sh to (re)establish a session.",
            file=sys.stderr,
        )
        sys.exit(1)
    return result.stdout.strip()


def get_salt_token(password: str) -> str:
    """Authenticate to Salt API and return X-Auth-Token."""
    resp = httpx.post(
        f"{SALT_URL}/login",
        json={"username": "hermes-infra", "password": password, "eauth": "pam"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["return"][0]["token"]


def run_salt_command(tgt: str, fun: str, arg: list | None = None) -> dict:
    """Execute a Salt command against target minion via Salt REST API."""
    password = get_salt_password()
    token = get_salt_token(password)

    payload = [
        {
            "client": "local",
            "tgt": tgt,
            "fun": fun,
            "arg": arg or [],
        }
    ]

    resp = httpx.post(
        SALT_URL,
        json=payload,
        headers={"X-Auth-Token": token},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["return"][0]


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: salt_client.py <target_minion> <function> [arg1] [arg2] ...")
        sys.exit(1)

    minion = sys.argv[1]
    function = sys.argv[2]
    arguments = sys.argv[3:]

    result = run_salt_command(minion, function, arguments)
    print(json.dumps(result, indent=2))
