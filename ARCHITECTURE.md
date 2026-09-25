# Architecture

Working assumptions as of project start (2026-09-22). Verify against the
catalog before trusting any of this in a future session — hardware/software
state on `w_workstation` changes as LocalForge work continues.

## Core design principle: network resources are agent capabilities

Hermes isn't just "a chat UI backed by a local model." The home network's
existing resources (compute, storage, the ability to host a web page, etc.)
are meant to become capabilities *the agent itself* can use and eventually
control — implementation-agnostic. E.g. "the agent can host a web page it
built" matters; *which* web server software does it, or which host it runs
on, doesn't. Keep this in mind when deciding where new pieces live: prefer
designs where a capability is something Hermes can invoke/control, not just
something Claude Code wired up once by hand.

## What's real right now

- **`hermes-vps`** (Vultr High Performance AMD, Dallas TX): Dedicated 2 vCPU,
  4GB RAM, 100GB NVMe. Runs the official Nous Research `HermesAgent` Ubuntu 24.04
  marketplace image, hermes-agent v0.19.0. Codex (`openai-codex`/`gpt-5.6-sol`,
  via linked ChatGPT Plus) is the default model provider. Docker + Dokploy
  installed (Dokploy's own Traefik disabled to avoid conflicting with
  Caddy's existing 80/443; Dokploy panel on :3000, localhost-only). A real
  firewall now exists (previously none at all).
- **`w_workstation`** (192.168.40.100, Windows 11, Georgia Pacific-managed
  via `BPNET` domain, Zscaler) has the actual GPU: an NVIDIA RTX A4000,
  16GB VRAM. As of 2026-09-25, **Ollama** (not LM Studio — see BACKLOG.md
  model-choice note) runs here as a genuine SYSTEM-level Windows service
  (no login dependency), models stored on `E:\Ollama Models`, bound to the
  LAN + WireGuard tunnel subnet. Managed remotely via Salt (this machine is
  an accepted Salt minion; `server` is the Salt master). LM Studio remains
  installed but is not the primary path — its Electron/GUI-session model
  proved awkward for remote/Salt management compared to Ollama's headless
  service model.
- **`server`** (192.168.40.250, Ubuntu 24.04) is the existing Docker host
  and Salt master — already runs Nginx Proxy Manager, AdGuard (LAN DNS),
  Portainer, the catalog (`catalog-db`/`catalog-api`), and persistent home
  services. As of 2026-09-25, also runs the WireGuard tunnel endpoint
  (dials out to hermes-vps, self-healing via keepalive, no home router
  port forwarding needed) and a Squid proxy (built for a Zscaler bypass
  that turned out unnecessary — left running, restricted to
  `w_workstation` only, in case it's useful later).
- **Remote access — decided (2026-09-22):** password-gated web UI behind the
  existing DuckDNS domain (`theguylab.duckdns.org`) or direct authenticated
  Hermes web interface / Telegram / Signal interface.
- `LocalForge`'s bridge already proves out the core idea (Claude Code / an
  agent process talking to LM Studio's OpenAI-compatible API over LAN) —
  the code at `Home Claude/LocalForge/bridge/server.py` is a working
  reference for the HTTP contract, timeouts, and `finish_reason == "length"`
  gotchas already discovered there.

## Network Topology & Subnet Tunnel

**Live as of 2026-09-25** (verified end-to-end: ping + catalog API + Salt
ports all reachable from hermes-vps over the tunnel). Tunnel subnet is
`10.60.0.0/24` (hermes-vps `10.60.0.1`, server `10.60.0.2`). The VPS
connects to the home fileserver via a site-to-site WireGuard tunnel,
enabling subnet routing so Hermes can address any LAN IP directly:

```
[VPS: Hermes + Dokploy] (Vultr Dallas)
         │
         │  Encrypted WireGuard Subnet Tunnel
         ▼
[Home Fileserver: 192.168.40.250] (server)
   ├── net.ipv4.ip_forward = 1
   └── iptables NAT / IP Forwarding enabled
         │
         ├──► 192.168.40.100:1234  (w_workstation / LM Studio)
         ├──► 192.168.40.x         (Salt / Storage / Home Services)
         └──► Entire 192.168.40.0/24 Home Subnet
```

Torrents, heavy media, and storage stay 100% on the home network via console/scripts,
ensuring zero bandwidth penalties on the VPS.

## Execution & Routing Tiers

1. **Always-On Hub (VPS - Vultr High Performance AMD):** Runs `hermes serve`,
   Dokploy (for managing web services and Docker containers via MCP), and CLI/chat interfaces.
2. **Free Local Inference (Home LAN):** LM Studio on `w_workstation` (RTX A4000) reached
   over the WireGuard tunnel for the bulk of agent queries.
3. **Frontier Model Fallback (Flat Subscription):** User's existing $20/mo ChatGPT Plus
   subscription linked directly via Hermes's native link+code flow.
4. **On-Demand Burst Compute & Sandboxing (Modal):** Serverless compute tier
   ($0 idle cost, pay-per-second) for heavy agent batch scripts, compilation, or untrusted
   code execution via `nousresearch/hermes-modal`.
