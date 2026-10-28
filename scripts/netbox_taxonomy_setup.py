#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]
# ///
"""One-time (idempotent) NetBox taxonomy setup for the Salt-based ecosystem sync.

Creates the minimum object graph every synced device needs to exist (NetBox
requires site + device_role + device_type on every dcim.device), plus custom
fields to hold data NetBox's typed schema doesn't model directly - notably
the full raw grains dump, so nothing collected is lost even when it isn't
individually mapped to a typed field.

Safe to re-run: every create is get-or-create by slug/name.
"""
import os

import httpx

NETBOX_URL = os.environ.get("NETBOX_URL", "http://192.168.40.100:8080")
NETBOX_TOKEN = os.environ["NETBOX_TOKEN"]  # nbt_<key>.<secret> - set in environment, never hardcoded

client = httpx.Client(
    base_url=NETBOX_URL,
    headers={"Authorization": f"Token {NETBOX_TOKEN}", "Content-Type": "application/json"},
    timeout=30,
)


def get_or_create(path: str, match: dict, create_body: dict) -> dict:
    resp = client.get(path, params=match)
    resp.raise_for_status()
    results = resp.json()["results"]
    if results:
        return results[0]
    resp = client.post(path, json=create_body)
    if resp.status_code >= 400:
        raise RuntimeError(f"POST {path} failed ({resp.status_code}): {resp.text}")
    return resp.json()


def main() -> None:
    site = get_or_create(
        "/api/dcim/sites/",
        {"slug": "home-lab"},
        {"name": "Home Lab", "slug": "home-lab", "status": "active",
         "description": "Mark's home network - synced from Salt, see scripts/netbox_sync.py"},
    )
    print(f"site: {site['id']} {site['name']}")

    manufacturer = get_or_create(
        "/api/dcim/manufacturers/",
        {"slug": "generic"},
        {"name": "Generic", "slug": "generic"},
    )
    print(f"manufacturer: {manufacturer['id']} {manufacturer['name']}")

    device_type = get_or_create(
        "/api/dcim/device-types/",
        {"slug": "generic-host"},
        {"manufacturer": manufacturer["id"], "model": "Generic Host", "slug": "generic-host",
         "u_height": 0, "is_full_depth": False},
    )
    print(f"device_type: {device_type['id']} {device_type['model']}")

    roles = {}
    for name, slug, color in [
        ("Server", "server", "2196f3"),
        ("Workstation", "workstation", "9c27b0"),
        ("VPS", "vps", "ff9800"),
    ]:
        role = get_or_create(
            "/api/dcim/device-roles/",
            {"slug": slug},
            {"name": name, "slug": slug, "color": color},
        )
        roles[slug] = role
        print(f"device_role: {role['id']} {role['name']}")

    platforms = {}
    for name, slug in [("Ubuntu Linux", "ubuntu"), ("Windows", "windows")]:
        platform = get_or_create(
            "/api/dcim/platforms/",
            {"slug": slug},
            {"name": name, "slug": slug},
        )
        platforms[slug] = platform
        print(f"platform: {platform['id']} {platform['name']}")

    custom_fields = [
        {
            "name": "salt_minion_id", "label": "Salt Minion ID", "type": "text",
            "object_types": ["dcim.device"], "description": "Minion ID this device is reachable as via Salt, if managed.",
        },
        {
            "name": "is_salt_minion", "label": "Salt Managed", "type": "boolean",
            "object_types": ["dcim.device"], "default": False,
        },
        {
            "name": "last_scan", "label": "Last Scan (UTC)", "type": "text",
            "object_types": ["dcim.device"], "description": "ISO8601 timestamp of the last sync that touched this device.",
        },
        {
            "name": "last_scan_mode", "label": "Last Scan Mode", "type": "select",
            "object_types": ["dcim.device"],
            "choice_set": "__scan_mode_choices__",
        },
        {
            "name": "grains_raw", "label": "Raw Salt Grains", "type": "json",
            "object_types": ["dcim.device"],
            "description": "Full grains.items dump from the last full scan - catch-all so nothing collected is lost.",
        },
    ]
    choice_set = get_or_create(
        "/api/extras/custom-field-choice-sets/",
        {"name": "scan_mode_choices"},
        {"name": "scan_mode_choices", "extra_choices": [["full", "full"], ["quick", "quick"]]},
    )
    print(f"choice_set: {choice_set['id']} scan_mode_choices")

    for cf in custom_fields:
        if cf.get("choice_set") == "__scan_mode_choices__":
            cf["choice_set"] = choice_set["id"]
        existing = client.get("/api/extras/custom-fields/", params={"name": cf["name"]}).json()["results"]
        if existing:
            print(f"custom_field: {cf['name']} (exists)")
            continue
        resp = client.post("/api/extras/custom-fields/", json=cf)
        if resp.status_code >= 400:
            raise RuntimeError(f"POST custom-field {cf['name']} failed ({resp.status_code}): {resp.text}")
        print(f"custom_field: {resp.json()['id']} {cf['name']} (created)")

    print("\nTaxonomy ready.")


if __name__ == "__main__":
    main()
