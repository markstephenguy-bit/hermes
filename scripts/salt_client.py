#!/usr/bin/env python3
"""Dedicated Salt API client for Hermes infrastructure management.
Executes commands against the Salt Master REST API at http://192.168.40.2:8000
using vaulted hermes-infra credentials over direct HTTP (zero SSH involvement).
"""
import os
import sys
import json
import httpx

SALT_URL = "http://192.168.40.2:8000"
VAULT_ITEM_NAME = "salt-hermes-infra"


def get_salt_password() -> str:
    """Retrieve the salt-hermes-infra password from Vaultwarden.

    Vaultwarden (via the bw CLI or the bitwarden MCP connector) is the sole
    secrets source - see Hermes's CLAUDE.md. This script never fetches or
    stores the plaintext itself; the caller must supply it fresh for this
    invocation only, e.g.:

        export SALT_HERMES_INFRA_PASSWORD="$(bw get password salt-hermes-infra)"
    """
    password = os.environ.get("SALT_HERMES_INFRA_PASSWORD")
    if not password:
        print(
            f"SALT_HERMES_INFRA_PASSWORD not set - export it for this invocation only "
            f"(e.g. via `bw get password {VAULT_ITEM_NAME}` or the bitwarden MCP connector), "
            f"never as a standing default.",
            file=sys.stderr,
        )
        sys.exit(1)
    return password


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
