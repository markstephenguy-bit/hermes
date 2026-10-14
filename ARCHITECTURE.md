# Architecture

Model configuration and the preparation recipe below were reviewed on
2026-10-07. Older network history retains its dates; verify live inventory
against the catalog. The recipe is a proposed configuration and research
sequence, not a claim that its settings have been deployed or optimized.

**Infra note (2026-10-11):** the "What's real right now" section below still
described the Vultr VPS, which was destroyed 2026-10-10 and replaced with a
Hostinger box — fixed in place below. The Qwen-heavy model prep recipe later
in this file is mostly provider-agnostic (about `w_workstation`/Qwen tuning,
not which VPS hosts the gateway) and hasn't been re-audited line-by-line; if
anything there mentions Vultr or Codex-as-fallback specifically, treat that as
stale and check [NEXT_SESSION.md](NEXT_SESSION.md) instead.

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

**Inference update (2026-10-13):** `w_workstation:8090` now runs Qwen3.5-9B Q4_K_M on mainline llama.cpp with a 64,000-token serving window. Hermes uses `custom:local-qwen`; its model ID is the Windows GGUF path advertised by `/v1/models`. The older Qwen3.6/ik_llama.cpp descriptions in the research recipe below are historical.

- **`hermes-vps`** (Hostinger KVM 2, Phoenix US): `srv2051520.hstgr.cloud`,
  `31.220.53.141`, 2 vCPU/8GB/100GB NVMe, plain Ubuntu 24.04 (not a vendor
  app template). **The prior Vultr box (207.148.2.224) was destroyed
  2026-10-10** — Vultr is gone both as the VPS host and as an LLM provider.
  Runs hermes-agent v0.21.6 via the official install.sh (not a marketplace
  image). Main model is local Qwen3.5-9B (`provider: custom:local-qwen`, mainline llama.cpp on
  `w_workstation:8090`); fallback is `deepseek/deepseek-v4.1-flash` via
  **Nous Portal** (`provider: nous`) — Codex is not configured as a fallback
  on this box. `hermes-gateway.service` and `hermes-dashboard.service` are
  systemd `--user` services under the `hermes` user (not system-level units).
  **Public dashboard (added 2026-10-11):** Caddy (native apt install, not
  Docker) reverse-proxies `https://theguylab.duckdns.org` → the dashboard
  (loopback `127.0.0.1:9119`), HTTP Basic Auth, auto-TLS via Let's Encrypt.
  Note `theguylab.duckdns.org` was **repointed from the home public IP to
  this VPS** — home's previously-public WordPress/NPM services are no longer
  reachable at that domain from the internet (deliberate tradeoff, decided
  2026-10-11, not an accident). Hostinger has its own hPanel-level firewall
  *in addition to* ufw — both must allow a port, and hPanel changes need an
  explicit "Synchronize" click to actually apply. No Dokploy on this box
  (that was a Vultr-only install, not recreated).
- **Curated knowledge vault** (added 2026-10-14):
  `/home/hermes/knowledge-vault` is a VPS-local Markdown folder, mounted
  read-write into the Hermes Docker sandbox at `/vault`. The bundled Obsidian
  skill uses `OBSIDIAN_VAULT_PATH=/vault` with file tools. This is separate
  from Hindsight's conversational memory. The mount is intentionally limited
  to the vault; the sandbox does not mount the whole Hermes home directory.
  Sync, backup, and automated curation are not configured yet.
- **`w_workstation`** (192.168.40.100, Windows 11, Georgia Pacific-managed
  via `BPNET` domain, Zscaler) currently serves Qwen3.5-9B Q4_K_M
  through mainline llama.cpp on port 8090. Its `/v1/models` response
  advertises the Windows GGUF path as the model ID and `n_ctx: 64000`.
  Hermes pins that exact ID and per-model context limit in its custom provider.
- **`server`** (192.168.40.250, Ubuntu 24.04) is the Docker host for
  persistent home services unrelated to the automation/networking backbone
  — Nginx Proxy Manager, AdGuard (LAN DNS), Portainer, WordPress, Plex,
  MeshCentral, Beszel, DuckDNS. Previously also ran the catalog, WireGuard
  tunnel endpoint, Squid, and Salt master/API — all four migrated off
  after `server` had repeated unclean crashes 2026-09-29/30 with no clear
  software root cause (still unconfirmed; sleep targets masked as a
  mitigation/test). Still runs its own `salt-minion`, pointed at the new
  master like every other minion.
- **`fileserver`** (192.168.40.2, Ubuntu 24.04) — previously just Samba file
  shares + a Beszel monitoring agent, now home to the entire migrated
  automation/networking stack, each piece a separate Docker container for
  compartmentalization: `catalog-db`/`catalog-api`, Squid (same ACL as
  before), the WireGuard tunnel endpoint (same keypair/identity preserved
  from `server` so hermes-vps needed zero config changes — WireGuard
  peers are keyed by public key, not source IP), and `salt-master`+`salt-api`
  (`cdalvaro/docker-salt-master`, minion *identity*/accepted-keys preserved
  from `server`'s PKI, though the container generated its own new master
  keypair on first start regardless — each of the 6 minions had their
  cached master-pubkey cleared and `master:` config repointed). All four
  migrations completed and verified 2026-09-30.
- **Remote access — decided (2026-09-22):** password-gated web UI behind the
  existing DuckDNS domain (`theguylab.duckdns.org`) or direct authenticated
  Hermes web interface / Telegram / Signal interface.
- `LocalForge`'s bridge already proves out the core idea (Claude Code / an
  agent process talking to LM Studio's OpenAI-compatible API over LAN) —
  the code at `Home Claude/LocalForge/bridge/server.py` is a working
  reference for the HTTP contract, timeouts, and `finish_reason == "length"`
  gotchas already discovered there.

## Network Topology & Subnet Tunnel

Tunnel subnet is `10.60.0.0/24`. **Re-established 2026-10-10** against the new
Hostinger VPS after the Vultr box was destroyed (fileserver's side kept its
identity — same container, same keypair, re-peered to the new VPS public key).
`fileserver`'s WireGuard runs as a Docker container (`linuxserver/wireguard`,
`--net=host`), native `wg-quick` on the VPS side. The VPS has a stable public
IP and listens; fileserver (behind home NAT, no router port-forward) dials
out to it — this direction, not the reverse, is why no home port-forwarding
is needed for the VPS↔fileserver leg.

```
[hermes-vps: 10.60.0.1] (Hostinger, 31.220.53.141 — stable public IP, listens)
         │
         │  Encrypted WireGuard tunnel (fileserver dials out, no home port-forward)
         ▼
[fileserver: 10.60.0.2 / 192.168.40.2] (Docker container)
   ├── net.ipv4.ip_forward = 1
   └── iptables NAT + explicit FORWARD ACCEPT (wg0<->enp4s0)
         │
         ├──► 192.168.40.100:8090 (w_workstation / llama.cpp)
         ├──► 192.168.40.x         (Salt / Storage / Home Services)
         └──► Entire 192.168.40.0/24 Home Subnet
```

**Third peer added 2026-10-11: laptop (`10.60.0.3`).** Same VPS-as-relay
pattern — the laptop dials the VPS (which already has a stable public IP and
open port), the VPS forwards into the already-working fileserver tunnel. This
lets the laptop reach the full home LAN from anywhere (e.g. work, behind a
different NAT) with **no home router changes** — the alternative of the
laptop dialing fileserver's real public IP (`66.170.221.155`) directly would
have required port-forwarding on the home router, deliberately avoided.
Required on the VPS: the laptop added as a `[Peer]` in `/etc/wireguard/wg0.conf`
(`AllowedIPs = 10.60.0.3/32`), `net.ipv4.ip_forward=1`, and a
`ufw route allow in on wg0 out on wg0` rule (ufw's routed-traffic default is
deny, which silently blocks exactly this kind of peer-to-peer forwarding).
Required on fileserver's WireGuard container: the VPS peer's `AllowedIPs` had
to be widened from `10.60.0.1/32` (only the VPS itself) to `10.60.0.0/24`,
otherwise fileserver's own cryptokey routing drops anything relayed from the
new laptop IP as untrusted. **Not auto-started** — bring up manually with
`sudo wg-quick up wg0` on the laptop when away from home (config already
installed at `/etc/wireguard/wg0.conf`); bring down with `wg-quick down` when
physically on the home LAN, since otherwise `AllowedIPs` routes all LAN
traffic through the VPS relay instead of the direct connection.

Torrents, heavy media, and storage stay 100% on the home network via console/scripts,
ensuring zero bandwidth penalties on the VPS.

## Execution & Routing Tiers

1. **Always-On Hub (VPS - Hostinger KVM 2):** Runs `hermes serve` and
   CLI/chat interfaces. No Dokploy on this box (Vultr-only, not recreated).
2. **Local Inference (Home LAN):** Qwen3.5-9B Q4_K_M via mainline llama.cpp;
   no per-token API charge, with electricity and shared-compute costs.
3. **External Models:** Fallback is `deepseek/deepseek-v4.1-flash` via Nous
   Portal, not Codex — Vultr/Codex-as-fallback is retired. The user wants
   capability-based selection, not an automatic single destination.
4. **Tool Execution:** Docker is the configured terminal backend. Modal
   credentials are staged according to the catalog, but it is not the active
   terminal backend. Execution location is independent of inference location.

## Qwen-heavy model preparation recipe

### Objective and verified starting point

Make Hermes the daily alternative to Claude Code across coding and personal-agent
functions, giving local Qwen substantial responsibility for complete tasks.
The user does substantial Visual Studio and other multi-language coding alongside
research, browser, images and general assistance; coding is a first-class workload.
Excessive Codex quota consumption is the problem, not reported poor
Codex answer quality. Qwen is considered for every call but need not run first.
The capability-routing proposal below supersedes the earlier fixed Codex tier.
Optimize correct completed work, response time, human intervention, and cloud
cost together. A local-token percentage alone is not a success measure.

Read-only VPS inspection on 2026-10-07 found:

- Main: `model.provider=local`, `model.default=qwen3.6-35b-a3b`, router at
  `http://127.0.0.1:11500/v1`, `model.context_length=65536`.
- Fallback: legacy `fallback_model` selects `openai-codex/gpt-5.6-sol`.
- Compression: explicitly uses Vultr `nvidia/DeepSeek-V3.2-NVFP4`, timeout 120s.
- MCP servers: catalog, search, infra, vault. Terminal backend: Docker.
- Deployed router differs from the repository: it routes image requests toward
  a cloud endpoint and exempts tool calls from empty-content rejection. Its
  streaming wrapper still constructs a text-only delta. No deployment repair
  was performed by this review.

The official Qwen model includes a vision encoder; the current local endpoint
advertises text only. Local vision is a runtime/projector compatibility and
performance investigation, not an inherent model impossibility. The model's
native context also differs from the smaller configured serving window.
See the [Qwen model card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B).

### Function-to-model map

These are recommended roles, not assertions that every optional integration is
installed. Every enabled tool needs a real availability and round-trip check.

| Hermes function | Recommended default | What must be prepared and tested |
| --- | --- | --- |
| Chat, planning, todo, clarification | Qwen | Instructions, task state, relevant project context, instruction-following tests |
| Codebase search, edits, tests, Git | Qwen owns ordinary tasks end to end | Real workspace mounts, runtimes, patch tools, test commands, Git identity/access, cancellation and diff checks |
| Difficult debugging, architecture, review | Best evaluated stronger model for that task; Codex is optional | Explicit escalation route, complete evidence/handoff, preserve ownership through hard execution |
| Terminal, processes, programmatic tool calls | Qwen selects actions; tools execute them | Docker persistence, host selection, exit codes, background-process handles and bounded output |
| Skills and artifact creation | Qwen plus skill-specific tools | Read skill requirements; document/rendering/media engines are separate dependencies |
| Web research and extraction | Qwen plus existing search/fetch tools | Search availability, citations, full-page retrieval, pagination, handling untrusted content; no grounded model required by default |
| Browser DOM interaction | Qwen | Browser installation/session persistence, DOM tools, download handling, exact browser execution host |
| Screenshots, image/PDF-page understanding | One tested vision route; evaluate local Qwen vision | Actual image input through Hermes and its adapter; OCR, diagrams, multiple images; dedicated `auxiliary.vision` route |
| Computer use and visual UI debugging | Qwen plus vision, or a vision-capable agent for the full loop | Screenshot-action-observation cycle, coordinate accuracy and recovery; compare helper latency against direct multimodal control |
| Context compression | Retain working Vultr route initially; compare Qwen | Preserve user constraints, paths, unresolved errors, tool state and decisions; compressor context must fit its input; check latency |
| Catalog memory, graph recall, session recall | Qwen orchestrates existing storage/search | Atomic writes, relation edges, evidence provenance; semantic recall requires a separate dimension-compatible embedding provider |
| Titles, memory flush, background review, MCP sampling | Explicit local route where supported; optional jobs disabled if not useful | Inventory actual call sites and hidden fallbacks; verify which jobs invoke an LLM and prioritize interactive work |
| Smart approvals | Existing policy with separately tested reviewer | Do not equate short output with easy decisions; uncertain cases escalate; credentials remain outside model-visible results |
| Delegation and optional MoA | Qwen for scoped subjobs; MoA off by default | Queue for one local inference slot, bounded depth/iterations, isolated workspaces for writers, inherited credentials/fallback verified |
| Cron, monitoring, messaging, kanban | Deterministic jobs when possible; Qwen for interpretation | Per-job tools/model, no overlapping duplicate runs, delivery target, cancellation, execution/delivery authorization |
| Speech input, spoken replies | Dedicated STT/TTS engines around Qwen | Transcription accuracy, audio dependencies, first-audio latency, interruption; cloud fallback only if needed |
| Image/video generation and optional video understanding | Specialized media provider on demand | Provider/model/key, separate price accounting and artifact return; not a text-model fallback |
| Infra, vault, Home Assistant and other connectors | Qwen calls bounded APIs | Service availability, target host, tool schemas, secret injection and concrete verification; frontier assistance for difficult reasoning |

Current Hermes docs describe independent auxiliary configuration and task-specific
fallbacks, but installation behavior must be checked against its own source:
[configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration).
The installed registry includes optional and platform-gated tools, so counting
registry entries does not prove that those tools are usable in a given session.

### Recommended starting configuration

1. Keep the current Qwen quantization/runtime as the baseline. Preserve WDDM
   because the workstation also drives a display. Reconcile deployed router
   source into version control and repair streaming before tuning model quality.
2. Use capability roles rather than a fixed provider ladder: local Qwen,
   economy overflow, vision/research specialist and stronger reasoning. Roles
   may share one model if evaluations justify it. Codex is not the presumed
   stronger model or universal fallback. Keep existing compression working until
   its replacement passes quality/latency tests.
3. Give Qwen complete ordinary coding tasks, including multi-file work when
   tests can verify it. Route directly to a specialist when an established capability or quality
   boundary justifies it; a failed local attempt is not required. Tool responses
   or multiple files alone are not such boundaries.
4. Keep 65,536 as the initial serving ceiling. Start testing compaction around
   45–48K total input tokens, reserving the rest for generation and tool growth.
   Count system instructions, tools, history and attachments. Test 32K/64K/128K
   as separate profiles; 128K is conditional on runtime, memory, quality and
   latency, not an immediate setting change.
5. Use model-author sampling as the starting point, and verify the server
   honors each parameter. For precise coding, the published thinking profile
   is temperature 0.6, top_p 0.95, top_k 20, min_p 0, presence penalty 0,
   repetition penalty 1. Test thinking on/off and template compatibility;
   unsupported flags must not silently masquerade as working optimizations.
6. Pilot 4K routine and 8K difficult-response generation budgets, including
   reasoning where the server counts it. Treat these as latency experiments;
   truncation triggers budget adjustment or escalation, not acceptance of an
   incomplete answer. Benchmark an adequately budgeted reference profile too.
7. Start with one concurrent local generation. Queue auxiliary work and local
   subagents across sessions; per-task auxiliary limits alone do not create a
   global queue. Parallel tools can still run where safe without parallel LLMs.
8. Prefer search, focused reads, diffs and stored tool output over repeated full
   files. Keep stable prompts/cache prefixes. Measure actual cache reuse;
   do not assume it from a cache flag. Use programmatic tools to batch routine
   reads and reduce model round trips.
9. Expose a coding-focused tool selection during coding and load other function
   groups when needed. Keep all required capabilities accessible through explicit
   profiles; distinguish function availability from injecting every schema into
   every turn.
10. Separate capability routing, quality escalation, outage fallback and spending
    policy. Make routing decisions at task start and meaningful checkpoints,
    avoiding an extra local judge request on every routine tool iteration.
    Start investigating after two attempts that reproduce the same failure with
    no new evidence; allow one bounded frontier rescue before checkpointing and
    reporting persistent failure. These are proposed policy values to calibrate.
11. Keep task identity and action results across provider changes. Timeouts after
    a side effect require checking state before retrying. A provider failure
    must not reset retry/spend counters or resend a completed external action.
12. Count main, auxiliary, fallback, media, subagent and external compute costs.
    Reserve estimated spend before concurrent calls and reconcile actual usage.
    Retain the existing Codex quota alert; use separate counters for subscription
    limits and API dollars. $20 is a benchmark, not a monthly hard cutoff.

### Research and evaluation, in order

**A. Establish the executable contract.** Pin Hermes source/build, router hash,
ik_llama build, GGUF checksum, chat template and model IDs. Export a secret-free
route inventory showing main, every auxiliary slot, delegates, scheduled jobs,
media and MCP-initiated sampling. Verify effective environment overrides and
fallbacks; config text alone does not prove which model is called.

**B. Prove tools before grading intelligence.** Run through the complete Hermes
path, with streaming and non-streaming: single and sequential tool calls, IDs,
null content, arguments with escaped strings/nested objects, tool errors,
truncation, cancellation and resumption. Test multiple calls only if advertised.
Exercise both fresh and long sessions. Capture machine-checkable traces without
secret values. Unsupported tool modes must be disabled or adapted explicitly.

**C. Tune Qwen on this workstation.** Keep the current Q4_K_M/Q8-KV baseline;
vary one dimension at a time: thinking, output budget, context size, cache
reuse, CPU/GPU expert placement, threads, batch size and speculation. Compare
larger quantization or alternative runtime only after establishing the baseline.
Measure cold/warm time to first token, prefill/decode, peak RAM/VRAM, queue wait,
total task time and correctness. Include auxiliary contention. Do not infer
throughput from free VRAM alone or from another machine's benchmark.

**D. Prove each specialist adds value.** Test local vision runtime/projector
support without disturbing the working text service; compare real screenshots
against one current cloud vision endpoint. Compare compression by retained
facts and latency. Check STT/TTS and media independently. Use provider model
lists, official docs, actual account quotas and end-to-end probes, not brand
names as evidence of modality or entitlement.

**E. Compare full agent workflows.** The user is already stress-testing Qwen in
Antigravity; incorporate those results rather than duplicate that work. Record
model/quantization, runtime, context, tools, language/project, task, outcome,
retries, latency and external calls. Separate model limitations from harness
or tool failures, then validate representative successes in Hermes itself.
As a starting sample, use 12 coding tasks across the user's actual languages
and Visual Studio projects plus 12 research/browser/vision/general tasks;
add coverage for remaining enabled functions before qualifying them. This is
an evaluation allocation, not a measured workload share. Coding should include
repository navigation, multi-file changes, debugging, builds/tests, dependency
changes and regression checks, with complexity and context varied separately.
Use representative user work and explicit success criteria. Compare local-only
Hermes, hybrid Hermes and the user's actual Claude Code setup on equivalent
workspaces/inputs, with repeated runs for variable cases. Judge patches by
tests and review, citations by sources, and actions by observed state. Track
human corrections, total latency, paid spend and quota use; expand weak categories.

**F. Verify recovery and adopt gradually.** Test local busy/offline, tunnel loss,
cloud rate limit, context exhaustion, interrupted tools, catalog unavailable and
concurrent sessions. Cloud inference can preserve conversation during a home
outage but cannot restore access to home-only tools. Pilot ordinary daily work,
then increase Qwen responsibility where observed success supports it. Enable
each remaining function when its readiness check passes; do not omit functions
merely because coding is the first adoption milestone.

Deliverables: an effective route inventory, measured benchmark results, a
version-compatible config patch, and rollback instructions. The current recipe
is the research-backed starting point; the optimized final configuration is the
one that wins these workload tests.

### Capability routing and cost optimization (2026-10-07)

**User priority:** Hermes remains the originator and owns task state. Consider
local Qwen for every inference, prefer it when it meets the task's quality and
latency requirements, and bypass it when a known specialist advantage warrants
that. External API spending is expected. Substantial Visual Studio and other
multi-language coding joins research, browser, images and general assistance
as a first-class workload. Excessive Codex quota use, rather
than answer-quality dissatisfaction, motivates removing the universal fallback.

**Proposed dispatcher:** First avoid inference for deterministic operations;
then filter eligible models by actual endpoint modalities, context capacity,
tool protocol, availability and data policy. Apply measured per-function quality
rules before selecting by total expected cost and latency. Qwen receives a
preference among qualifying options. Ambiguous new jobs may use a small local
classification call, but routine calls use a policy lookup with no extra LLM.
Established task ownership avoids model churn inside a coherent reasoning
phase; reconsider Qwen at phase boundaries and when requirements change.

Log the candidate set, why Qwen was selected or excluded, requested and actual
model, task/parent IDs, tokens/cache/latency, retry reason and observed outcome.
The dispatcher must cover auxiliary calls, delegates, schedules and MCP sampling,
not only the main chat endpoint. Treat quality routing as an explicit decision;
do not simulate an outage with HTTP 503 just to switch models. A provider outage
can use an eligible peer without automatically consuming Codex quota.

| Role | Initial candidates to compare | Routing policy |
| --- | --- | --- |
| Default reasoning and tool orchestration | Existing local Qwen3.6-35B-A3B | Routine research, DOM browsing, chat, memory, straightforward code and infra; compare fast/thinking profiles on same weights |
| Economy external overflow | DeepSeek `deepseek-flash` versus GPT-6 Luna API | Known local quality gaps, latency-sensitive work or local outage; choose by measured outcome, not price alone |
| Visual/research specialist | Gemini 3.8 Flash versus economy models above and local vision | Dense screenshots, diagrams, source synthesis and optional native grounding; Qwen can consume specialist observations when full remote ownership is unnecessary |
| Stronger synthesis/reasoning | Claude Sonnet 5.5 versus GPT-6.1 Sol API | Difficult conflicting evidence and tasks with a demonstrated quality gap; occasional higher tier only if it improves outcomes |
| Existing Codex subscription | Current linked route | Optional explicitly selected resource; not the automatic sink for all failures or background work |

These are candidates, not benchmark winners or confirmed account entitlements.
GPT-6 Luna requires Responses for reasoning plus function calling; its Chat
Completions function-calling path requires reasoning effort `none`. Verify
Hermes adapter support before selecting it. New Claude models also have tool
and thinking compatibility changes; test the actual adapter. A hosted Qwen
endpoint is another availability/latency option but still incurs cloud calls
and does not inherently remove same-model quality weaknesses.

**Mixtures worth comparing:** (A) Qwen + Gemini + one stronger model, for simple
coverage; (B) add economy overflow only when it reduces cost without reducing
success; (C) Qwen + one economy multimodal model + stronger model, dropping
Gemini if it adds no measured value; (D) local vision/helper or larger local
model, accepting additional resource contention/load time; (E) selective
OpenRouter Auto for genuinely uncertain external jobs; (F) multiple-model
review for expensive-to-get-wrong conclusions only. Do not run every mixture
or every candidate on every ordinary request.

OpenRouter can be just external transport with explicit model IDs, or an
external model selector through Auto; ordinary provider routing chooses a host
for a model rather than whether to use local Qwen. Keep local selection inside
Hermes. Auto has no additional routing fee; Standard credit purchases carry
a 5.5% platform fee. Its allowed-model lists and cost settings help constrain
external selection, but do not establish quality for this user's workload.
Sources: [Auto Router](https://openrouter.ai/docs/guides/routing/routers/auto-router),
[fees](https://openrouter.ai/business),
[provider routing](https://openrouter.ai/docs/guides/routing/provider-selection).

**Price snapshot:** USD per million uncached input / billed output tokens,
standard service, no tool fees. This is a comparison baseline, not a bill forecast.

| Candidate | Input / output | 20K input + 2K output example |
| --- | --- | --- |
| DeepSeek Flash, off-peak / peak | $0.15 / $0.60; $0.30 / $1.20 | $0.0042 / $0.0084 |
| GPT-6 Luna API | $0.10 / $0.50 | $0.0030 |
| Gemini 3.8 Flash | $0.75 / $3.75 through 2026-12-31 | $0.0225 |
| Claude Sonnet 5.5 | $2 / $10 | $0.0600 |
| GPT-6.1 Sol API | $2 / $10 | $0.0600 |
| Claude Opus 5.5 | $4 / $20 | $0.1200 |

Primary prices: [DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/),
[Google](https://ai.google.dev/gemini-api/docs/pricing),
[OpenAI](https://developers.openai.com/api/docs/pricing),
[Anthropic](https://platform.claude.com/docs/en/about-claude/pricing).
Google lists doubled Flash prices starting 2027-01-01. Account/model availability,
image tokenization, cache writes/reads/storage, reasoning tokens, provider markup,
search queries, retries, voice/media, electricity and hosting must be accounted
for separately. Identical text need not tokenize equally across models.

Illustration only: 3,000 total model calls/month, 70% local, 20% DeepSeek peak,
8% Gemini, 2% Sonnet, each external call averaging 20K input and 2K output,
costs $14.04 in uncached API tokens. Ten calls per user task and background calls
can make monthly inference volume much larger than the number of user messages.
Do not interpret the example shares as an achievable quality-preserving target.
Compute spend from all billed attempts, then divide by successful tasks. Add
human rework and latency as separate objectives instead of claiming a cheap
token rate proves a better system.

**Local-model alternatives:** MoE active parameters describe computation, not
total weight storage. Approximate raw 4-bit weight floors are 40GB for 80B and
61GB for 122B, before quantization metadata, caches and runtime buffers. System
RAM plus VRAM is not a single freely interchangeable pool on this workstation.

| Candidate | Why evaluate | Limitation / priority |
| --- | --- | --- |
| Current Qwen3.6-35B-A3B | Tune and enable compatible local vision first | Highest-priority baseline; current runtime advertises text only |
| Qwen3.6-27B dense | Quality comparison for general/visual work | Higher active computation can hurt latency under offload; benchmark |
| Qwen3.5-9B helper | Small vision or background route | Test screenshot fidelity and contention; do not assume two resident models fit |
| Qwen3.5-122B-A10B MoE | Larger multimodal local quality experiment | Tight memory headroom and more active work; not the first production swap |
| Qwen3-Coder-Next 80B-A3B | Coding-specific local alternative worth comparison for substantial multi-language work | Text-only; evaluate gains against current Qwen and model loading/storage overhead |
| GLM-4.7-Flash / gpt-oss-20b | Alternative compact text/tool baselines | Must beat Qwen on actual work; not an automatic solution to visual offloads |

Sources: [Qwen 27B](https://huggingface.co/Qwen/Qwen3.6-27B),
[Qwen 9B](https://huggingface.co/Qwen/Qwen3.5-9B),
[Qwen 122B](https://huggingface.co/Qwen/Qwen3.5-122B-A10B),
[Coder Next](https://huggingface.co/Qwen/Qwen3-Coder-Next),
[GLM](https://huggingface.co/zai-org/GLM-4.7-Flash),
[gpt-oss deployment](https://developers.openai.com/cookbook/articles/gpt-oss/run-transformers).
Internal expert selection within a MoE is distinct from Hermes choosing models.

**Evidence and remaining work:** Historical VPS accounting from 2026-09-25 to
2026-10-07 02:22 UTC records 837 main Codex calls, 168 approval calls and four
title calls with the same model. Router logs show 49 upfront escalations and
70 post-response escalations, including 64 labelled empty response. These span
older configurations and are not proof of current rates or that all empty
responses were valid tool calls. Incomplete/new-model accounting and zero cost
fields prevent a reliable current monthly forecast. Repair and instrument the
path before treating any local/cloud split as measured.

Next experiment: sample representative research/browser/image/general tasks;
replay across the shortlisted local profiles and 2–3 external candidates with
identical tools and bounded context. Score sourced accuracy, visual correctness,
completion, human corrections, retries and p50/p95 end-to-end latency. Keep a
held-out set when turning results into static routing rules, repeat variable
cases, and retain routes that provide a meaningful quality/cost/latency benefit.
This is the path to an optimized mix; no paid inference benchmarks or runtime
changes were performed during this research pass.

Additional primary references:
- [Provider resolution](https://hermes-agent.nousresearch.com/docs/developer-guide/provider-runtime)
- [Mixture of Agents](https://hermes-agent.nousresearch.com/docs/user-guide/features/mixture-of-agents)
- [Voice setup](https://hermes-agent.nousresearch.com/docs/user-guide/features/voice-mode)
- [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp)
