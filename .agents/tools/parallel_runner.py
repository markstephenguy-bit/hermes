#!/usr/bin/env python3
"""
Parallel Runner Tool for Antigravity
Provides multi-threaded batch execution of shell commands, HTTP requests, or file processing.
"""
import sys
import json
import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
import urllib.error

def run_command(cmd: str, cwd: str = None) -> dict:
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        return {
            "command": cmd,
            "exit_code": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr
        }
    except Exception as e:
        return {
            "command": cmd,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e)
        }

def http_get(url: str, headers: dict = None) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read().decode('utf-8')
            return {"url": url, "status": r.status, "content": body}
    except Exception as e:
        return {"url": url, "status": -1, "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Multithreaded task execution for Antigravity tools")
    sub = parser.add_subparsers(dest="action")

    # Commands batch
    cmd_p = sub.add_parser("commands")
    cmd_p.add_argument("cmd_file", help="JSON file containing list of commands to run concurrently")
    cmd_p.add_argument("--workers", type=int, default=8, help="Max worker threads")

    # HTTP GET batch
    http_p = sub.add_parser("http")
    http_p.add_argument("url_file", help="JSON file containing list of URLs to fetch concurrently")
    http_p.add_argument("--workers", type=int, default=8, help="Max worker threads")

    args = parser.parse_args()

    if args.action == "commands":
        with open(args.cmd_file) as f:
            commands = json.load(f)
        
        results = []
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_cmd = {executor.submit(run_command, c): c for c in commands}
            for future in as_completed(future_to_cmd):
                results.append(future.result())
        print(json.dumps(results, indent=2))

    elif args.action == "http":
        with open(args.url_file) as f:
            urls = json.load(f)

        results = []
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_url = {executor.submit(http_get, u): u for u in urls}
            for future in as_completed(future_to_url):
                results.append(future.result())
        print(json.dumps(results, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
