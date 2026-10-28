#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]
# ///
"""Sync known Salt-managed hosts into NetBox so it stays a live map of the
home-lab ecosystem rather than a one-time snapshot.

Two modes, matching how an AI agent actually needs this:
  --mode full   Every known minion, every collected fact (interfaces, IPs,
                 uptime, memory, disk, OS release). Meant to run hourly on a
                 schedule - this is the deep "augment context" pass.
  --mode quick  Reachability + IP/interface delta only, for one minion (or
                 all). Meant to be triggered on demand (e.g. via the MCP
                 tool in infra_mcp.py) when something might have changed and
                 a full rescan isn't warranted yet.

Uses only Salt functions already permitted for the hermes-infra eauth user
(test.*, cmd.*, status.*, disk.*, network.*, service.*) - no grains.* needed.
Writes directly to NetBox's REST API with the admin token (the MCP sidecar
is intentionally read-only, so it can't be used for this).

Run via scripts/netbox_sync_run.sh, which sources .env for secrets - never
invoke this directly without SALT_PASS/NETBOX_TOKEN set in the environment.
"""
import argparse
import ipaddress
import os
import time
from datetime import datetime, timezone

import httpx

SALT_URL = os.environ.get("SALT_URL", "http://192.168.40.2:8000")
SALT_USER = os.environ.get("SALT_USER", "mark")
SALT_PASS = os.environ["SALT_PASS"]
NETBOX_URL = os.environ.get("NETBOX_URL", "http://192.168.40.100:8080")
NETBOX_TOKEN = os.environ["NETBOX_TOKEN"]

# Known hosts. Platform determines which OS-release probe to use; role/platform
# slugs must already exist in NetBox (see scripts/netbox_taxonomy_setup.py).
# Add new hosts here as they come under Salt management.
MINIONS = {
    "fileserver":   {"platform": "linux",   "role_slug": "server",      "platform_slug": "ubuntu"},
    "server":       {"platform": "linux",   "role_slug": "server",      "platform_slug": "ubuntu"},
    "laptop":       {"platform": "linux",   "role_slug": "workstation", "platform_slug": "ubuntu"},
    "w_workstation": {"platform": "windows", "role_slug": "workstation", "platform_slug": "windows"},
    "hermes-vps":   {"platform": "linux",   "role_slug": "vps",         "platform_slug": "ubuntu"},
}

# Interface name prefixes that are noise, not real topology - Docker bridges,
# veth pairs, loopback, Hyper-V/WSL virtual switches.
NOISE_INTERFACE_PREFIXES = (
    "lo", "docker", "br-", "veth", "vEthernet", "Loopback", "virbr",
)

SITE_ID = 1          # Home Lab, created by netbox_taxonomy_setup.py
DEVICE_TYPE_ID = 1   # Generic Host
HOME_LAN = ipaddress.ip_network("192.168.40.0/24")


class SaltClient:
    """Minion facts are pulled with calls to Salt's REST API - same token-cache
    pattern as infra_mcp.py so repeated runs don't re-login every call."""

    def __init__(self) -> None:
        self._token = ""
        self._expire = 0.0
        self._http = httpx.Client(timeout=30)

    def _ensure_token(self) -> str:
        if self._token and time.time() < self._expire - 30:
            return self._token
        resp = self._http.post(
            f"{SALT_URL}/login",
            data={"username": SALT_USER, "password": SALT_PASS, "eauth": "pam"},
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        ret = resp.json()["return"][0]
        self._token = ret["token"]
        self._expire = ret["expire"]
        return self._token

    def call(self, target: str, function: str, args: list[str] | None = None,
              powershell: bool = False) -> dict:
        payload: dict = {"client": "local", "tgt": target, "fun": function}
        if args:
            payload["arg"] = args
        if powershell:
            payload["kwarg"] = '{"shell": "powershell"}'
        resp = self._http.post(
            SALT_URL + "/",
            headers={"X-Auth-Token": self._ensure_token(), "Accept": "application/json"},
            data=payload,
        )
        resp.raise_for_status()
        ret = resp.json()["return"][0]
        return ret.get(target, {})


def collect_facts(salt: SaltClient, minion_id: str, platform: str, deep: bool) -> dict | None:
    """Returns None if the minion didn't respond at all (treated as offline)."""
    if not salt.call(minion_id, "test.ping"):
        return None

    facts: dict = {"interfaces": salt.call(minion_id, "network.interfaces")}
    uptime = salt.call(minion_id, "status.uptime")
    if isinstance(uptime, dict):
        facts["uptime_days"] = uptime.get("days")
    elif isinstance(uptime, (int, float)):
        facts["uptime_days"] = round(uptime / 86400, 1)

    if not deep:
        return facts

    facts["meminfo"] = salt.call(minion_id, "status.meminfo")
    facts["disk"] = salt.call(minion_id, "disk.usage")

    if platform == "linux":
        out = salt.call(minion_id, "cmd.run", ["grep PRETTY_NAME /etc/os-release; uname -r; nproc"])
        lines = out.splitlines()
        facts["os_release"] = lines[0].split("=", 1)[-1].strip('"') if lines else None
        facts["kernel"] = lines[1] if len(lines) > 1 else None
        facts["cpu_count"] = lines[2] if len(lines) > 2 else None
    else:
        out = salt.call(
            minion_id, "cmd.run",
            ["(Get-CimInstance Win32_OperatingSystem).Caption; "
             "(Get-CimInstance Win32_Processor).NumberOfLogicalProcessors"],
            powershell=True,
        )
        lines = out.splitlines()
        facts["os_release"] = lines[0].strip() if lines else None
        facts["cpu_count"] = lines[1].strip() if len(lines) > 1 else None

    return facts


def pick_primary(interfaces: dict) -> tuple[str, str] | None:
    """Returns (interface_name, ip_address) for the interface that should be
    primary_ip4, preferring the real home-LAN address, then any public IP,
    then the WireGuard mesh address, skipping noise interfaces entirely."""
    candidates: list[tuple[int, str, str]] = []  # (priority, ifname, ip)
    for ifname, data in interfaces.items():
        if any(ifname.startswith(p) for p in NOISE_INTERFACE_PREFIXES):
            continue
        for entry in data.get("inet", []):
            addr = entry.get("address")
            if not addr:
                continue
            try:
                ip = ipaddress.ip_address(addr)
            except ValueError:
                continue
            if ip.is_loopback or ip.is_link_local:
                continue
            if ip in HOME_LAN:
                priority = 0
            elif ifname == "wg0":
                priority = 2
            elif ip.is_private:
                priority = 3
            else:
                priority = 1  # public IP
            candidates.append((priority, ifname, addr))
    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0])
    return candidates[0][1], candidates[0][2]


class NetBoxClient:
    def __init__(self) -> None:
        self.http = httpx.Client(
            base_url=NETBOX_URL,
            headers={"Authorization": f"Token {NETBOX_TOKEN}", "Content-Type": "application/json"},
            timeout=30,
        )

    def get_one(self, path: str, **params) -> dict | None:
        resp = self.http.get(path, params=params)
        resp.raise_for_status()
        results = resp.json()["results"]
        return results[0] if results else None

    def upsert(self, path: str, match: dict, body: dict) -> dict:
        existing = self.get_one(path, **match)
        if existing:
            resp = self.http.patch(f"{path}{existing['id']}/", json=body)
        else:
            resp = self.http.post(path, json=body)
        if resp.status_code >= 400:
            raise RuntimeError(f"{path} upsert failed ({resp.status_code}): {resp.text}")
        return resp.json()


def sync_device(nb: NetBoxClient, minion_id: str, meta: dict, facts: dict, mode: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    interfaces = facts.get("interfaces", {})
    primary = pick_primary(interfaces)

    device_body = {
        "name": minion_id,
        "device_type": DEVICE_TYPE_ID,
        "role": {"slug": meta["role_slug"]},
        "platform": {"slug": meta["platform_slug"]},
        "site": SITE_ID,
        "status": "active",
        "custom_fields": {
            "salt_minion_id": minion_id,
            "is_salt_minion": True,
            "last_scan": now,
            "last_scan_mode": mode,
        },
    }
    if facts.get("os_release"):
        device_body["comments"] = (
            f"OS: {facts.get('os_release')} | kernel: {facts.get('kernel', 'n/a')} | "
            f"cpus: {facts.get('cpu_count', 'n/a')} | uptime: {facts.get('uptime_days', 'n/a')}d"
        )
    if mode == "full":
        device_body["custom_fields"]["grains_raw"] = facts

    device = nb.upsert("/api/dcim/devices/", {"name": minion_id}, device_body)

    for ifname, data in interfaces.items():
        if any(ifname.startswith(p) for p in NOISE_INTERFACE_PREFIXES):
            continue
        addrs = [e.get("address") for e in data.get("inet", []) if e.get("address")]
        if not addrs:
            continue
        iface = nb.upsert(
            "/api/dcim/interfaces/",
            {"device_id": device["id"], "name": ifname},
            {"device": device["id"], "name": ifname, "type": "virtual",
             "mac_address": data.get("hwaddr") if data.get("hwaddr", "").count(":") == 5 else None,
             "enabled": data.get("up", True)},
        )
        for addr in addrs:
            try:
                if ipaddress.ip_address(addr).is_loopback or ipaddress.ip_address(addr).is_link_local:
                    continue
            except ValueError:
                continue
            prefixlen = 24 if ipaddress.ip_address(addr) in HOME_LAN else 32
            ip_obj = nb.upsert(
                "/api/ipam/ip-addresses/",
                {"address": f"{addr}/{prefixlen}"},
                {"address": f"{addr}/{prefixlen}", "status": "active",
                 "assigned_object_type": "dcim.interface", "assigned_object_id": iface["id"]},
            )
            if primary and primary[1] == addr:
                nb.http.patch(f"/api/dcim/devices/{device['id']}/", json={"primary_ip4": ip_obj["id"]})

    print(f"  synced {minion_id} ({mode}) -> device {device['id']}"
          + (f", primary_ip {primary[1]}" if primary else ", no primary IP found"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["full", "quick"], default="full")
    parser.add_argument("--target", default="*", help="minion id, or * for all known minions")
    args = parser.parse_args()

    salt = SaltClient()
    nb = NetBoxClient()
    targets = list(MINIONS) if args.target == "*" else [args.target]

    print(f"Running {args.mode} scan against: {', '.join(targets)}")
    for minion_id in targets:
        meta = MINIONS.get(minion_id)
        if not meta:
            print(f"  skip {minion_id}: not in MINIONS registry")
            continue
        facts = collect_facts(salt, minion_id, meta["platform"], deep=(args.mode == "full"))
        if facts is None:
            print(f"  {minion_id}: offline/unreachable, marking as such in NetBox")
            existing = nb.get_one("/api/dcim/devices/", name=minion_id)
            if existing:
                nb.http.patch(f"/api/dcim/devices/{existing['id']}/", json={"status": "offline"})
            continue
        sync_device(nb, minion_id, meta, facts, args.mode)

    print("Done.")


if __name__ == "__main__":
    main()
