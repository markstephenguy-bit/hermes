#!/usr/bin/env python3
"""
Roku ECP (External Control Protocol) client for Hermes.
Supports discovery, status queries, remote keypresses, and launching apps.
"""

import sys
import time
import argparse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

DEFAULT_ROKU_IP = "192.168.40.206"
PORT = 8060

KEY_ALIASES = {
    "play": "Play",
    "pause": "Play",
    "playpause": "Play",
    "home": "Home",
    "back": "Back",
    "select": "Select",
    "ok": "Select",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "volup": "VolumeUp",
    "volumeup": "VolumeUp",
    "voldown": "VolumeDown",
    "volumedown": "VolumeDown",
    "mute": "VolumeMute",
    "rev": "Rev",
    "rewind": "Rev",
    "fwd": "Fwd",
    "fastforward": "Fwd",
    "replay": "InstantReplay",
    "info": "Info",
    "star": "Info",
    "options": "Info",
    "backspace": "Backspace",
    "search": "Search",
    "enter": "Enter",
    "power": "Power",
    "poweroff": "PowerOff",
    "poweron": "PowerOn",
}


class RokuController:
    def __init__(self, ip: str = DEFAULT_ROKU_IP, port: int = PORT):
        self.ip = ip
        self.port = port
        self.base_url = f"http://{self.ip}:{self.port}"

    def _get(self, path: str) -> str:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def _post(self, path: str, data: bytes = b"") -> tuple[int, str]:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, data=data, method="POST", headers={"User-Agent": "Hermes/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")

    def get_device_info(self) -> dict:
        xml_data = self._get("/query/device-info")
        root = ET.fromstring(xml_data)
        return {child.tag: child.text for child in root}

    def get_active_app(self) -> dict:
        xml_data = self._get("/query/active-app")
        root = ET.fromstring(xml_data)
        app = root.find("app")
        if app is not None:
            return {
                "name": app.text,
                "id": app.get("id"),
                "version": app.get("version"),
                "type": app.get("type"),
            }
        return {"name": "None", "id": None}

    def get_apps(self) -> list[dict]:
        try:
            xml_data = self._get("/query/apps")
            if "not allowed in Limited mode" in xml_data:
                return [{"error": "Limited mode enabled on Roku. Enable in Settings > System > Advanced system settings > Control by mobile apps."}]
            root = ET.fromstring(xml_data)
            apps = []
            for app in root.findall("app"):
                apps.append({
                    "name": app.text,
                    "id": app.get("id"),
                    "version": app.get("version"),
                    "type": app.get("type"),
                })
            return apps
        except urllib.error.HTTPError as e:
            if e.code == 403:
                return [{"error": "HTTP 403 Forbidden: ECP is in Limited mode on the Roku device."}]
            raise

    def send_key(self, key_name: str) -> bool:
        cmd = KEY_ALIASES.get(key_name.lower(), key_name)
        status, _ = self._post(f"/keypress/{cmd}")
        return status == 200

    def type_text(self, text: str) -> bool:
        for char in text:
            status, _ = self._post(f"/keypress/Lit_{urllib.parse.quote(char)}")
            if status != 200:
                return False
            time.sleep(0.05)
        return True

    def launch_app(self, app_id: str) -> bool:
        status, _ = self._post(f"/launch/{app_id}")
        return status == 200


def main():
    parser = argparse.ArgumentParser(description="Hermes Roku Controller")
    parser.add_argument("--ip", default=DEFAULT_ROKU_IP, help=f"Roku IP address (default: {DEFAULT_ROKU_IP})")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    subparsers.add_parser("status", help="Get device information and active app")

    # key
    key_parser = subparsers.add_parser("key", help="Send keypress (e.g. Home, Play, Select, VolumeUp, VolumeDown)")
    key_parser.add_argument("name", help="Name of key to press")

    # type
    type_parser = subparsers.add_parser("type", help="Type a text string into the active input")
    type_parser.add_argument("text", help="Text to type")

    # apps
    subparsers.add_parser("apps", help="List installed apps")

    # launch
    launch_parser = subparsers.add_parser("launch", help="Launch an app by ID")
    launch_parser.add_argument("app_id", help="App ID (e.g. 837 for YouTube)")

    args = parser.parse_args()
    roku = RokuController(ip=args.ip)

    if args.command == "status":
        info = roku.get_device_info()
        active = roku.get_active_app()
        print(f"Device: {info.get('friendly-device-name', 'Roku')} ({info.get('model-name', 'Unknown')})")
        print(f"Location: {info.get('user-device-location', 'Unknown')}")
        print(f"IP: {args.ip}")
        print(f"Power: {info.get('power-mode')}")
        print(f"ECP Mode: {info.get('ecp-setting-mode')}")
        print(f"Active App: {active.get('name')} (ID: {active.get('id')})")

    elif args.command == "key":
        ok = roku.send_key(args.name)
        print(f"Keypress '{args.name}': {'OK' if ok else 'FAILED'}")

    elif args.command == "type":
        ok = roku.type_text(args.text)
        print(f"Type '{args.text}': {'OK' if ok else 'FAILED'}")

    elif args.command == "apps":
        apps = roku.get_apps()
        for app in apps:
            if "error" in app:
                print("Note:", app["error"])
            else:
                print(f"[{app['id']}] {app['name']}")

    elif args.command == "launch":
        ok = roku.launch_app(args.app_id)
        print(f"Launch {args.app_id}: {'OK' if ok else 'FAILED'}")


if __name__ == "__main__":
    main()
