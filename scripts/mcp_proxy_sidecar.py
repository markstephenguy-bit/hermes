#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fastmcp>=2.0",
#     "httpx>=0.27",
# ]
# ///
"""Sidecar MCP server behind the `mcp_proxy` gateway (MCPHub/UplinkCrate).

Composes the existing cognee/infra/hermes MCP servers into one process over
streamable-HTTP so every harness (Claude Code, Codex, Antigravity, Hermes)
can reach all three through a single gateway registration instead of one
registration per server per harness. See scripts/cognee_cloud_mcp.py,
scripts/infra_mcp.py, and scripts/hermes_mcp.py for what each namespace
actually does - this file only wires them together, it doesn't reimplement
any of their tools.

Tools are namespaced on mount: cognee_recall, infra_salt_run, hermes_chat,
etc. (FastMCP's mount() prefixes every tool/resource/prompt name with
"<namespace>_" automatically.)

Binds to 127.0.0.1 only - the MCPHub gateway container on the same host is
the sole intended caller, reached via the docker bridge gateway IP, not the
public LAN interface. No auth of its own; MCPHub is the trust boundary.

Credentials for the mounted servers (SALT_*, HERMES_*, COGNEE_CLOUD_*) are
loaded from MCP_PROXY_CREDENTIALS_FILE (default
~/.config/mcp-proxy/credentials.env, mode 0600) before those modules are
imported, since cognee_cloud_mcp.py reads env at import time and
infra_mcp.py/hermes_mcp.py expect their run.sh wrappers to have sourced
.env already - that wrapper doesn't exist when FastMCP mounts them as
Python objects instead of spawning them as stdio subprocesses.
"""
import os
import sys
from pathlib import Path

CREDS_FILE = Path(
    os.environ.get("MCP_PROXY_CREDENTIALS_FILE", "")
    or (Path.home() / ".config" / "mcp-proxy" / "credentials.env")
)
if CREDS_FILE.exists():
    for line in CREDS_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP  # noqa: E402

import cognee_cloud_mcp  # noqa: E402
import infra_mcp  # noqa: E402
import hermes_mcp  # noqa: E402

mcp = FastMCP(name="mcp_proxy_sidecar")
mcp.mount(cognee_cloud_mcp.mcp, namespace="cognee")
mcp.mount(infra_mcp.mcp, namespace="infra")
mcp.mount(hermes_mcp.mcp, namespace="hermes")

if __name__ == "__main__":
    host = os.environ.get("MCP_PROXY_SIDECAR_HOST", "127.0.0.1")
    port = int(os.environ.get("MCP_PROXY_SIDECAR_PORT", "8700"))
    mcp.run(transport="http", host=host, port=port)
