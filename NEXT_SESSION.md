# Session Brief — Migrate mcp_proxy off MCPHub to sidecar-only FastMCP

**This replaces the prior brief (Cognee Cloud migration), which is long
finished — see CLAUDE.md and git history for that. This file now seeds the
next active piece of work.**

## Why

MCPHub (the Docker gateway fronting `mcp_proxy`, port 3100 on `fileserver`)
has been judged too heavy/cumbersome for fast access. Decision: drop
MCPHub, expose `mcp_proxy_sidecar.py` directly as a standalone FastMCP
server instead of running it behind MCPHub. Raised 2026-11-18–20 in a
Claude Code research/thinking session — **not started anywhere yet**. The
2026-11-16 memory marking `mcp_proxy` "COMPLETE" describes the MCPHub+
sidecar architecture that this migration replaces, not the new target —
don't read that as this already being done.

## Current state (last verified live 2026-11-16, re-verify before trusting)

- **MCPHub/UplinkCrate**: Docker container on `fileserver`, port 3100,
  bearer auth, the single upstream every harness registers
  (`http://192.168.40.2:3100/mcp` LAN / `http://10.60.0.2:3100/mcp` from
  `hermes-vps` over the existing WireGuard tunnel).
- **`mcp_proxy_sidecar.py`**: systemd `--user` service on `fileserver`,
  currently loopback-only (`127.0.0.1` / `172.17.0.1:8700`). Mounts
  `cognee_cloud_mcp.py`, `infra_mcp.py`, `hermes_mcp.py` via FastMCP's
  `mount()`, plus `hermes_serve` proxying `hermes-vps`'s native
  `mcp-serve --tools` plugin via `create_proxy()`.
- **Four harness registrations all point at MCPHub, not the sidecar
  directly**: Claude Code (`.mcp.json` / `~/.claude.json`), Codex
  (`.codex/config.toml` + `~/.codex/config.toml`, bearer token via
  `MCP_PROXY_GATEWAY_TOKEN` env var), Antigravity
  (`~/.gemini/config/mcp_config.json`), Hermes (`hermes-vps`
  `~/.hermes/config.yaml`, bearer token literal in `headers`).

## What needs to happen

1. Give the sidecar its own network-reachable listener (not just
   loopback). Decide port (reuse 8700, or pick a new one) and bind
   address — needs to stay reachable the same way MCPHub currently is:
   `fileserver`'s LAN IP and over the WireGuard tunnel from `hermes-vps`.
2. Give the sidecar its own auth. MCPHub was providing bearer-token
   auth/RBAC; FastMCP has its own bearer-auth middleware/token-provider
   options. Reuse the existing `MCP_PROXY_GATEWAY_TOKEN` value so harness
   configs only need a new URL, not a new secret.
3. Confirm FastMCP's HTTP/streamable-HTTP server mode doesn't inherit the
   Docker-bridge-gateway reachability problem MCPHub's SSRF-allowlist fix
   was working around (`172.17.0.1`) — likely moot once MCPHub itself is
   gone, but verify nothing else in the sidecar's own networking assumed
   MCPHub as a hop.
4. Repoint all four harness registrations (the files listed above) from
   the MCPHub URL to the sidecar's new direct URL.
5. Test each harness against the new direct path **before** touching
   MCPHub: tool listing + one real call (e.g. `infra_salt_minion_status`)
   per harness, from both LAN and over WireGuard from `hermes-vps`.
6. Only after all four harnesses are verified on the new path: stop/remove
   the MCPHub container on `fileserver`. Don't decommission it earlier —
   it's currently the only thing providing MCP access to any harness,
   including whichever session runs this migration.

## Open decisions for the execution session

- Exact port/bind address for the sidecar's direct listener.
- Which FastMCP auth mechanism replaces MCPHub's bearer-auth/RBAC.
- Whether to keep MCPHub installed-but-stopped for a rollback window, or
  remove it outright once every harness is confirmed working.

## Source material

- Original MCPHub+sidecar build details, gotchas, and the SSRF-allowlist
  fix: Claude Code project memory `project_hermes_mcp_proxy_gateway.md`
  and this repo's CLAUDE.md, "One gateway for every harness" section.
- This migration decision was raised in a Claude Code research session
  2026-11-18–20 and had not been recorded anywhere until this file.

## Explicitly out of scope for whichever session picks this up

This was raised in a session explicitly framed as understanding/research-
only — no SSH, Salt, or live config changes happened there. This file is
the full handoff; nothing beyond it should be assumed already done.
