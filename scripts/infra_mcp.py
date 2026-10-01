#!/usr/bin/env python3
"""MCP server exposing home-lab infrastructure control (Salt first; MeshCentral
and Beszel to follow once their APIs are verified working) as tools for Hermes.

Salt auth token is cached in-process and transparently refreshed on expiry -
the single biggest annoyance of calling Salt's REST API by hand is tokens
silently expiring mid-session and every call needing a fresh login first.
"""
import os
import time

import httpx

from fastmcp import FastMCP

SALT_URL = os.environ.get("SALT_URL", "http://192.168.40.2:8000")
SALT_USER = os.environ.get("SALT_USER", "mark")
SALT_PASS = os.environ.get("SALT_PASS")  # must be set in the environment, never hardcoded

mcp = FastMCP(name="infra")

_token_cache: dict[str, float | str] = {"token": "", "expire": 0.0}


def _salt_token() -> str:
    """Return a valid Salt API token, logging in again if the cached one is missing or expired."""
    if _token_cache["token"] and time.time() < float(_token_cache["expire"]) - 30:
        return str(_token_cache["token"])
    if not SALT_PASS:
        raise RuntimeError("SALT_PASS not set in the environment")
    resp = httpx.post(
        f"{SALT_URL}/login",
        data={"username": SALT_USER, "password": SALT_PASS, "eauth": "pam"},
        headers={"Accept": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    ret = resp.json()["return"][0]
    _token_cache["token"] = ret["token"]
    _token_cache["expire"] = ret["expire"]
    return str(ret["token"])


def _salt_call(payload: dict) -> dict:
    token = _salt_token()
    resp = httpx.post(
        SALT_URL + "/",
        headers={"X-Auth-Token": token, "Accept": "application/json"},
        data=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def salt_run(target: str, function: str, args: list[str] | None = None, powershell: bool = False) -> dict:
    """Run a Salt function (e.g. 'test.ping', 'cmd.run') against a target minion or glob.

    Set powershell=True when running cmd.run on a Windows minion with a PowerShell command.
    """
    payload = {"client": "local", "tgt": target, "fun": function}
    if args:
        payload["arg"] = args
    if powershell:
        payload["kwarg"] = '{"shell": "powershell"}'
    return _salt_call(payload)


@mcp.tool
def salt_minion_status() -> dict:
    """Ping every known minion at once and report which are up/down."""
    return _salt_call({"client": "local", "tgt": "*", "fun": "test.ping"})


if __name__ == "__main__":
    mcp.run()
