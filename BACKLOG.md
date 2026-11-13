# Backlog / Open Questions

## Current priority: hermes-vps setup master list (2026-11-01)

Hermes moved from `server` to `hermes-vps` (31.220.53.141) this session —
this is the punch list for getting that instance to a genuinely finished,
working state. Supersedes nothing below as "wrong," just reflects that the
ground moved again; check this list first, then CAPABILITY_PARITY.md for
the broader CC-parity framing (needs its own refresh pass — several items
here resolve or update things it still describes as on `server`).

**P0 — functional gaps, blocking real use:**
- **Public dashboard access is broken.** `hermes.markstephenguy.com` over
  the normal internet/NPM/Authentik path doesn't work — confirmed a Docker
  bridge "hairpin" issue (SYN packets reach the host and get firewall-accepted,
  but the connection never completes) between the `npm` container and the
  dashboard process, root cause not found despite real diagnostic effort.
  Worked around with two alternate paths that **do** work: direct over the
  WireGuard mesh (`http://10.60.0.1:9119`, basic-auth protected) for
  WireGuard-reachable devices, and **SSH** (`hermes@31.220.53.141`, key
  `~/.ssh/hostinger_hermes_vps_ed25519`, deployed + verified this session) —
  Hermes Desktop is connected via SSH right now. The public path itself is
  still unfixed; only matters if non-WireGuard, non-SSH access is wanted
  (e.g. a browser from anywhere with just a password).
- **`infra` (Salt) and `netbox` MCP servers were never actually wired into
  Hermes.** `hermes mcp list` on `hermes-vps` confirms zero MCP servers
  configured. Instructions were given earlier for this but targeted the old
  `server` host, before the VPS migration decision — need to redo, this
  time on `hermes-vps`.
- **`server`'s fate is undecided** — update 2026-11-12: Mark confirmed
  `server` and `w_laptop` are turned off **on purpose** and will stay off
  until he can diagnose their hardware/software issues. Not a thing to fix
  or wait out; leave both alone until he says otherwise.

**P1 — needed for real confidence, not yet broken but not done:**
- **Nous Portal fallback model** — deliberately deferred by Mark, never
  configured. Main model is **gpt-oss-20b, served by LM Studio on
  `w_workstation`** (2026-11-12 correction — not Qwen/llama.cpp as earlier
  notes said); no fallback configured, so a tunnel hiccup means Hermes
  answers but can't think, not a clean outage.
- ~~Telegram round-trip not fully confirmed~~ — **RESOLVED 2026-11-12**:
  real two-way exchange verified (Mark messaged the bot, got a reply,
  confirmed in gateway.log).
- ~~LAN-wide convenience access~~ — **RESOLVED 2026-11-12** for `hermes-vps`:
  per-device `/etc/hosts` + Windows hosts entries (`hermes-vps` → the
  WireGuard IP `10.60.0.1`) plus a persistent route to `10.60.0.0/24` via
  fileserver, pushed to laptop/fileserver/w_workstation/w_desktop via Salt.
  Chosen over AdGuard-wide DNS rewrites or fixing the public path, since
  there aren't many LAN machines. `server`/`w_laptop` excluded — see above.

**P2 — hygiene, not blocking anything today:**
- **Hindsight has no backup/export cadence** — standing gap noted in
  CLAUDE.md, more load-bearing now that both Claude Code and Hermes depend
  on the same bank.
- **Old `server` Hermes install not decommissioned** — gateway stopped, but
  nothing uninstalled; revisit once the `server` hardware decision lands.
- **Docker resource limits** on `hermes-vps`'s 6 containers (Authentik x3,
  WordPress, WordPress DB, NPM) — done, using official/manufacturer
  recommended baselines as the starting point; revisit if real usage proves
  them wrong in either direction.
- **CAPABILITY_PARITY.md needs a refresh pass** — written while Hermes was
  on `server`; several things it describes have since moved, resolved, or
  changed shape (Hindsight is now the native plugin, not a generic MCP
  entry; host changed; NPM/dashboard findings are new).

## Historical: see CAPABILITY_PARITY.md for the earlier (2026-10-31) capability matrix

The Claude-Code-parity tracking that used to live inline below (P0-P2 from
the 2026-10-07 integration test) was superseded by a full capability
matrix and roadmap in [CAPABILITY_PARITY.md](CAPABILITY_PARITY.md)
(2026-10-31), built after Mark's 2026-10-28 decision to make Hermes his
primary AI harness. The 2026-10-07 findings below are kept for history —
several (vision, no fallback, destructive-action approval) are re-confirmed
still open above; others may be stale given the host moved off the VPS
entirely since then.

## Historical: integration punch-list from live capability testing (2026-10-07)

29 live probes run against Hermes's real agent API (pure local Qwen3.6-35B-A3B,
no Codex/cloud fallback) across three batteries — not raw-model benchmarks, the
actual Hermes toolset through its own `/v1/responses` endpoint. Full detail is in
the catalog (`hermes-integration-priority-list-2026-10-07` and the entities it
links to). The prior "not deployed or benchmark-certified" framing below is
superseded by this — it now is.

**P0 — fix before trusting Hermes with real work:**
- Tilde (`~`) path resolution bug: `write_file`/`patch` can silently target a
  different effective home directory than `terminal`/`read_file` in the same
  turn, while still reporting `verified: true`. Workaround today: always use
  absolute paths. Root-caused precisely: `is_container()` checks whether the
  *agent process* is containerized, not whether the *terminal backend* is —
  fires on any standard hermes-agent deployment using the docker terminal
  backend (the vendor's own recommended sandboxing pattern), not something
  specific to this install. Needs a real fix in hermes-agent's path-resolution
  layer. **Re-verified live on 2026-10-08 after a deliberate, vetted upgrade to
  v0.19.0 (which did fix the separate `/v1/skills` TypeError bug for free) —
  still broken.** The underlying code was substantially rewritten (new
  `terminal.home_mode` config: auto/real/profile) but the host-vs-container
  disagreement persists; now manifests as `write_file` resolving to
  `/home/hermes/...` while `terminal` resolves to `/root/...` under the
  now-correctly-configured docker terminal backend. Still vendored source, same
  overwrite-on-update caveat applies to any future patch.
- Destructive actions get zero human confirmation: a flagged recursive `rm -rf`
  was auto-approved by smart-approval with no pause, under
  `GATEWAY_ALLOW_ALL_USERS=true` on the unattended api_server surface. Needs an
  actual policy decision, not silent auto-approval.
- **No fallback provider, and the local model has zero concurrency headroom.**
  Live-reproduced: ~10 simultaneous model-requiring requests (an 8-way subagent
  fan-out plus 2 concurrent same-session calls) crashed the single-slot
  ik_llama.cpp server outright (Windows Task Scheduler recorded
  `STATUS_STACK_BUFFER_OVERRUN`) and took down all of Hermes, including the
  default daily-use profile, with no automatic recovery — the Codex fallback
  was intentionally removed for pure-local-Qwen mode. Restarting the model
  server wasn't even enough on its own; zombie retry loops inside the Hermes
  gateway kept re-occupying the single recovered slot until the gateway itself
  was restarted. **Decision (2026-10-07): a fallback provider must be restored,
  sequenced after the current issue-finding phase completes — not yet
  implemented.** Until then: never fire more than 1-2 concurrent
  model-requiring requests at this setup.
  **Requirement for when it's implemented:** the fallback path needs its own
  rate limit/circuit breaker, not just a model pointer reusing the existing
  retry logic — the exact zombie-retry storm that crashed the local model for
  free would, against a paid cloud API, turn into an unexpected bill. Cap
  retry/escalation attempts and fail closed instead of indefinitely hammering
  a paid endpoint.

**P1 — needed for daily-use parity with Claude Code:**
- Vision routing: confirmed hard floor (no mmproj, text-only local model), but
  screenshots are an established daily workflow need. Needs a routed
  vision-capable fallback (cloud or local VL model).
- `execute_code` is hard-blocked on the api_server (unattended) surface by
  design — not a model gap, works fine via the CLI. Decide: enable
  `approvals.unattended_mode: approve` for this surface, or standardize on
  terminal-based code execution as the permanent workaround.

**P2 — only if actually wanted:**
- `image_generate` is advertised enabled but has no real backend wired; needs
  a Nous Portal / Tool Gateway subscription or an alternative.
- No docker-in-docker visibility — the terminal sandbox can't see the host's
  real Docker containers; needs a host-level terminal backend or a dedicated
  container tool if managing containers on `server`/`fileserver` matters.

**Deferred on purpose** until functional completeness is proven (explicit user
call): hermes-vps has no firewall at all and the API server (`0.0.0.0:8642`)
is reachable from the raw internet, bearer-key-only auth.

The user does substantial Visual Studio and other multi-language coding alongside
research, browser, images and general assistance. Follow the
[capability-routing comparison](ARCHITECTURE.md#capability-routing-and-cost-optimization-2026-10-07):
Qwen is always considered, direct specialist routes are allowed, and Codex is
not the presumed fallback.

## Architecture guide review (2026-10-07)

Review findings are logged as linked `hermes` catalog entities; these are
open issues and proposals, not deployed changes:

- Repair the checked-in router's tool-call contract: null content crashes,
  empty content triggers fallback even for tool calls, and streaming drops
  tool-call payloads. Verify the deployed copy separately.
- Reconcile the guide with implementation: the repository router forces images
  local and has no spend ledger, monthly alerts, or tool-loop lock; repetitive
  text triggers fallback rather than stopping a task.
- Replace the proposed unconditional local tool-loop lock with task-level model
  ownership and bounded escalation. Track progress, retries, elapsed time,
  shared API spend reservations, and subscription quota separately.
- Verify current provider IDs and capabilities through the actual adapters;
  Google lists Gemini 2.0 Flash as shut down. Establish parity using complete
  coding tasks, image/tool round trips, and outage recovery, not weather-call
  smoke tests or an assumed 90% local workload share.
- Reconcile older budget-cap records with the later elastic-spend strategy;
  preserve $20 as a benchmark, and distinguish proposals from verified behavior.

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

## Local inference direction (2026-10-02)

User excludes Ollama-based hosting for the future local inference setup. Evaluate
vLLM and other runtimes that use GPU plus system RAM for larger models, including
ik_llama.cpp and KTransformers. Near-100-token/s reports are an evaluation target,
not verified workstation performance. Salt verified 64GB RAM (2x32GB at 2933 MT/s),
a Xeon W-2225 (4c/8t), and RTX A4000 16GB on PCIe 3.0 x16 on 2026-10-03. Earlier Ollama pull/configuration steps below
are historical and superseded. On 2026-10-07 the live API confirmed ik_llama.cpp
serving Qwen3.6-35B-A3B Q4_K_M on port 8090 with a 65,536-token context limit.

## Immediate Next Steps

Steps 1-3 below (connect, onboard Codex, Dokploy+WireGuard) are done as of
2026-09-25 — done by Claude Code directly rather than handed off to Hermes
as originally planned here, per explicit user request once the Desktop
app's OAuth flow proved too fragile to debug live. Current next steps:

1. **Validate Qwen's complete Hermes tool loop** using the existing ik_llama.cpp
   endpoint; the former Ollama model-pull step is superseded.
2. **Implement and measure the model-use recipe** above. Live config already
   selects local Qwen as main and Codex as fallback; quality routing, auxiliary
   policy and end-to-end reliability still need validation.
3. **Write `SOUL.md`/`USER.md`** on hermes-vps — drafted in conversation,
   never committed.
4. **Signal/Telegram gateway** (G7) — `hermes-gateway` running, no channel
   configured.

## Other open decisions
- **Cloud capability mix** — reopened 2026-10-07: linked Codex is the current
  fallback, but the user wants Qwen-preferred routing that reduces quota use;
  external API spending is accepted when justified by capability and results.
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
