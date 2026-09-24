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
  marketplace image. Hosts `hermes serve` and acts as the central hub and web
  presence, with full KVM root access to run Dokploy and the WireGuard home tunnel.
- **`w_workstation`** (192.168.40.100, Windows 11) has the actual GPU: an
  NVIDIA RTX A4000, 16GB VRAM. LM Studio is already running there with
  `gemma-4-12b-it@q8_0` loaded (~12GB) plus `nomic-embed-text-v1.5` for
  embeddings — roughly 4GB of headroom left before a second model could be
  loaded alongside it.
- **`server`** (192.168.40.250, Ubuntu 24.04) is the existing Docker host —
  already runs Nginx Proxy Manager, AdGuard (LAN DNS), Portainer, the
  catalog (`catalog-db`/`catalog-api`), and persistent home services.
  Acts as the home-side WireGuard gateway endpoint to route `192.168.40.0/24`
  traffic from the VPS to `w_workstation` and Salt.
- **Remote access — decided (2026-09-22):** password-gated web UI behind the
  existing DuckDNS domain (`theguylab.duckdns.org`) or direct authenticated
  Hermes web interface / Telegram / Signal interface.
- `LocalForge`'s bridge already proves out the core idea (Claude Code / an
  agent process talking to LM Studio's OpenAI-compatible API over LAN) —
  the code at `Home Claude/LocalForge/bridge/server.py` is a working
  reference for the HTTP contract, timeouts, and `finish_reason == "length"`
  gotchas already discovered there.

## Network Topology & Subnet Tunnel

The VPS connects to the home fileserver via a site-to-site WireGuard tunnel,
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
