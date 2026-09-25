# Backlog / Open Questions

## The fork that needs deciding first

Hermes is independent of LocalForge (decided 2026-09-22 — see catalog entity
`hermes-independent-of-localforge-2026-09-22`), so this is now a pure code-
reuse question, not a scope-boundary one:

- **(a) Share code with LocalForge** — reuse its existing LM Studio
  connection code / HTTP contract (`delegate_task` plumbing, `finish_reason`
  handling, etc.) as a starting point.
- **(b) Build Hermes's own client from scratch** — accept some duplication,
  keep LocalForge completely untouched.

Nothing else below should really be worked until this is picked, since it
determines where the code lives and what gets reused.

## Resolved

- **Remote access mechanism (2026-09-22):** password-gated web UI behind
  existing DuckDNS + Nginx Proxy Manager, path-based location. No VPN/tunnel
  client on the connecting device — see ARCHITECTURE.md for the reasoning
  (Georgia Pacific laptop constraint) and catalog entity
  `hermes-remote-access-decision-2026-09-22`.
- **Model choice, cloud tier (2026-09-23):** Codex (via linked ChatGPT
  Plus, `openai-codex`/`gpt-5.6-sol`) is the primary model on `hermes-vps`
  itself — resolved and live as of 2026-09-25 (G5 done).
- **Model choice, local tier (2026-09-25):** the earlier "must be Nous's
  Hermes line" preference (below) was superseded by a direct performance
  comparison once Ollama was actually being configured on `w_workstation`.
  Chose **`gpt-oss-20b`** (OpenAI, Apache 2.0, MoE) as the local primary —
  benchmarked as the best fit for 16GB VRAM + agentic tool-calling
  specifically (faster than dense alternatives at the same footprint),
  beating both Hermes-4-14B and Qwen3-14B on that axis. Paired with
  `qwen3-vl:8b` for screenshot/OCR understanding (user relies on
  screenshots heavily; none of the text-only candidates can see images)
  and `nomic-embed-text` for memory/RAG embeddings. Not yet pulled/running
  — see NEXT_SESSION.md.
  <details><summary>Original 2026-09-23 reasoning (superseded)</summary>
  The agent's model was Hermes (Nous Research's model line) — not an open
  evaluation, chosen because the user considered it best-in-class. Needs
  to fit `w_workstation`'s RTX A4000 16GB VRAM. See catalog entity
  `hermes-agent-model-is-hermes-2026-09-23`.
  </details>
- **VPS provider & deployment (2026-09-24):** Selected **Vultr High
  Performance AMD** in Dallas, TX (`vhp-2c-4gb-amd`, 2 vCPU, 4GB RAM, 100GB
  NVMe @ $24/mo + $4.80 daily backups) for ultra-low latency (~10-15ms) to
  East Texas home LAN, fast single-core clock for subagents, NVMe I/O, and no
  burstable CPU credit traps. Deployed turn-key official Nous Research
  `HermesAgent` Ubuntu 24.04 Marketplace image.
- **Bandwidth concern resolved (2026-09-24):** Non-issue. Heavy torrenting/media
  workflows execute completely on the home network via console/scripts. VPS
  traffic is strictly text tokens and orchestration (<50GB/mo), well within
  standard 4TB quota.
- **Compute burst tier (2026-09-24):** Modal confirmed as the on-demand
  serverless compute backend ($0/mo idle, pay-per-second, isolated untrusted
  agent code), complementary to local Dokploy.
- **Bootstrap handoff strategy (2026-09-24):** Onboard Hermes with existing
  $20/mo ChatGPT Plus subscription via native link+code flow. Once authenticated,
  Hermes takes over to execute its own remaining setup (Dokploy, WireGuard
  tunnel to home fileserver, LM Studio bridge).

## Immediate Next Steps

Steps 1-3 below (connect, onboard Codex, Dokploy+WireGuard) are done as of
2026-09-25 — done by Claude Code directly rather than handed off to Hermes
as originally planned here, per explicit user request once the Desktop
app's OAuth flow proved too fragile to debug live. Current next steps:

1. **Pull the local Ollama model package** on `w_workstation`
   (`gpt-oss-20b`, `qwen3-vl:8b`, `nomic-embed-text`) — see NEXT_SESSION.md.
2. **Wire Ollama into Hermes's fallback_providers/MoA config** so local is
   preferred and Codex is the ceiling-hit fallback (G1/G8).
3. **Write `SOUL.md`/`USER.md`** on hermes-vps — drafted in conversation,
   never committed.
4. **Signal/Telegram gateway** (G7) — `hermes-gateway` running, no channel
   configured.

## Other open decisions
- **Cloud fallback provider** — resolved in practice via existing $20 ChatGPT Plus subscription via native link+code flow.
- **UI implementation** — the *access path* is decided (above); the UI
  itself (Hermes Desktop / web interface on port 9119) is available out of the box with `hermes serve`.
- **Auth mechanism at the NPM Custom Location** — plain HTTP Basic Auth
  (simple, works immediately) vs. an app-level login page (nicer, more
  work).
- **Agent-controlled web hosting** — Dokploy MCP server on the VPS gives Hermes
  the native ability to deploy and manage containers/web apps directly.

## Non-goals (for now)

- Re-documenting the home network in this repo — that's the catalog's job.
- Standing up a second reverse proxy / DNS / tunnel stack — NPM + DuckDNS
  already does this job (decided above).
- Committing to specific software (LiteLLM, a specific model, a specific
  tunnel provider) before the LocalForge-vs-separate fork above is resolved.
