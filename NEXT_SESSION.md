# Session Seed — Hermes Default Profile, Post-Outage

This is the single most current record of infrastructure state for this
project — more current than ARCHITECTURE.md/BACKLOG.md. If you're an agent
(Claude Code, Codex, Antigravity, or otherwise) picking this project up cold,
read this file in full before touching anything. If you're a human in a chat
UI, paste this whole file as your opening message instead.

## 2026-10-11 (later still): public dashboard, DNS, laptop WireGuard peer

Done this session (not yet reflected anywhere except here + the catalog):

- **Public web dashboard for hermes-vps (Hostinger)**, reachable from any
  browser, anywhere, no client install: `https://theguylab.duckdns.org`,
  Basic Auth (`mark` / password in catalog vault, not repeated here). Native
  Caddy (apt, not Docker) reverse-proxies to the dashboard on loopback
  `127.0.0.1:9119` (`hermes-dashboard.service`, systemd `--user`, added
  alongside the existing `hermes-gateway.service`). Caddy's `reverse_proxy`
  needed an explicit `header_up Host {upstream_hostport}` — the dashboard
  has its own Host-header check and 400s if it sees the public domain name
  instead of the loopback host it's bound to.
- **`theguylab.duckdns.org` was deliberately repointed** from the home
  network's public IP to the VPS. This was an explicit tradeoff, confirmed
  with the user, not an accident: home's WordPress/NPM public-facing presence
  at that domain is now unreachable from the internet (LAN-internal access
  still fine via AdGuard's local DNS rewrite). If this needs reverting, a
  fresh DuckDNS subdomain is the clean fix (4 of 5 slots still free on the
  account) rather than un-repointing `theguylab`.
- **Two firewall layers on the Hostinger VPS, not one:** ufw (OS-level) *and*
  a separate Hostinger hPanel firewall (cloud-level) both gate inbound
  traffic independently. hPanel rule changes additionally require clicking
  **Synchronize** before they actually apply to the server — adding a rule
  alone isn't enough, confirmed by this session hitting exactly that trap
  (rules existed and looked active but traffic was still blocked until sync).
- **Laptop added as a third WireGuard peer (`10.60.0.3`)**, relayed through
  the VPS into the home LAN (not a direct connection to home's real public
  IP, which would have needed home router port-forwarding — deliberately
  avoided). Full detail and the exact config in ARCHITECTURE.md's Network
  Topology section. Config lives at `/etc/wireguard/wg0.conf` on the laptop.
  **Not auto-started.** Commands:
  - Away from home (e.g. at work): `sudo wg-quick up wg0`
  - Back home: `sudo wg-quick down wg0` (otherwise home-LAN traffic
    needlessly routes through the VPS relay instead of the direct LAN path)
- All of the above needs logging to the catalog + `scripts/export_catalog_memory.py`
  re-run + commit if that hasn't happened yet by the time you're reading this
  — check the catalog for entities tagged `hermes` dated 2026-10-11 to confirm.

## The one thing that matters most this session

The handoff from the previous session claimed Qwen was "confirmed working"
as the main model. **It was not** — `model.base_url` had silently drifted
to Nous Portal while `model.default` stayed a Qwen filename, so every
single request was 404ing the entire time. The previous session only
verified `model.default` as a config string match; it never fired a live
request. **Don't repeat that mistake**: after any config.yaml change here,
validate with an actual live round trip —
`hermes -z "Reply with exactly these three words and nothing else: <marker>"`
— not just a `hermes config get`.

## Current state — re-verified live 2026-10-10, not assumed

- **Default profile = model routing**, confirmed working end-to-end:
  - **Primary**: Qwen3.6-35B-A3B-Q4_K_M via `ik_llama.cpp` on
    `w_workstation` (192.168.40.100:8090), `provider: custom`,
    `base_url: http://192.168.40.100:8090/v1`, reached over WireGuard.
  - **Fallback**: `deepseek/deepseek-v4.1-flash` via **Nous Portal**
    (`provider: nous`). **Vultr Serverless Inference is gone entirely** —
    both the Vultr VPS host and Vultr as an LLM provider. Nous Portal
    (portal.nousresearch.com / inference-api.nousresearch.com) is the
    replacement for all cloud model access now. Nous OAuth already
    authenticated as mark.stephen.guy@gmail.com.
  - Set via `hermes config set fallback_providers "[{provider: nous, model: deepseek/deepseek-v4.1-flash}]"`
    — this flat key works and bypasses the broken `hermes fallback add`
    interactive wizard entirely. Confirmed with `hermes fallback list`.
  - **Vision aux**: `auxiliary.vision.provider` pinned explicitly to
    `nous` (was `auto`) — covers Qwen's text-only gap.
  - `agent.api_max_retries` lowered 3 → 1 for faster failover onto the
    fallback chain.
- **VPS**: `srv2051520.hstgr.cloud`, Hostinger KVM 2, IP `31.220.53.141`.
  SSH as `root` or `hermes`, key `~/.ssh/hostinger_hermes_vps_ed25519`.
- **WireGuard**: native `wg-quick`, 10.60.0.1/24 ↔ fileserver 10.60.0.2/24,
  0% packet loss, confirmed working.
- **Telegram**: connected, confirmed working live.

## Also done this session: auxiliary task mixture (2026-10-10, later)

Mark's direction: Qwen primary everywhere it's capable (cost control), Nous
Portal specifically where Qwen lacks capability or mistakes are costly —
not auto-routing everything to Nous, not staying 100% local either. Real
key names were confirmed by grepping hermes-agent's own compiled Desktop
UI bundle (`ModelsPage-*.js`), not guessed from the Desktop labels —
config.yaml's comments only documented 7 of the 12 auxiliary task types,
guessing the rest would have risked silent misconfiguration.

Set via `hermes config set auxiliary.<task>.provider nous`:
- **Nous**: `vision`, `approval`, `review`, `triage_specifier`, `kanban_decomposer`
- **Qwen (auto)**: `compression`, `skills_hub`, `mcp`, `title_generation`,
  `voice_chat`, `profile_describer`, `curator`

Verified live after gateway restart with another `hermes -z` literal-reply
test. See catalog entity `hermes-aux-task-model-mixture-2026-10-10`.

A full capability map (what's live/available/unexplored across all of
Hermes, not just model routing) was built as an artifact this session —
check the conversation history or ask Mark for the link if picking up
from here.

## Also done this session: concurrency cap (2026-10-10, later still)

`max_concurrent_sessions` was `null` (unlimited) — directly the root cause
of the 2026-10-07 crash (10 simultaneous requests hung Qwen's single
inference slot). Capped it at 3. Above that, new sessions get a clean
error instead of piling onto Qwen. Verified Qwen still answers after
restart. This significantly reduces the urgency of the circuit-breaker
item below — most of the pile-up that would trigger it can no longer
happen. Still worth building eventually, just not urgently.

Also confirmed and explained plainly: `auto` (used by 7 of the 12
auxiliary tasks) already means "Qwen first, for everyone, always" —
cloud only engages when Qwen's connection is actually broken, not
because another model seems better. This is already live, needs no
further setup. Verified against hermes-agent's own test suite
(`tests/agent/test_auxiliary_main_first.py`), not just the config.yaml
comment, which is stale/outdated documentation left over from an older,
reversed policy — don't trust that comment block if you read it again.

## Also done this session: memory system validated and restored (2026-10-11)

Validated all three kinds of Hermes memory. Findings: the Vultr→Hostinger
migration silently wiped `USER.md` (didn't exist at all), reset `MEMORY.md`
to near-empty, and deleted all projects (`hermes project list` → none) —
nobody had checked file *content* after the rebuild, only that services
were running. SOUL.md survived but was just the unmodified Hermes-seeded
default, never customized.

Fixed `USER.md` and `MEMORY.md`:
- Sourced from three places and cross-checked before writing: Claude
  Code's own memory of Mark, a tool-enabled agent's independent
  re-investigation of the catalog + a separate shared memory folder, and
  a second ChatGPT query that honestly declined facts it couldn't verify
  (good calibration check — no contradictions, no fabrication).
- `USER.md`: 1,337/1,375 chars. `MEMORY.md`: 1,761/2,200 chars (kept the
  one pre-existing validated entry about `computer_use`'s sandbox
  limitation, added the rest).
- Verified live, not just written: asked a fresh `hermes -z` session to
  state facts from each file; both echoed correct content back.
- Logged to catalog as `hermes-user-memory-restored-2026-10-11`.

**SOUL.md done too.** Replaced the never-touched Hermes-seeded default
(1,150 bytes). Kept what it already got right (direct/no-filler, honest
uncertainty, earned depth, pushback-when-right) and added two traits
tonight's lessons made obvious were missing: verify live before claiming
something works, and be a decisive executor rather than a hedging
auditor. Verified live — a fresh session correctly self-identified using
the new text. Logged as `hermes-soul-customized-2026-10-11`.

**Projects: done too — "Hermes Install" created.** Mark wanted a project
scoped to the Hermes install itself, separate from the global root
files. Real architecture check first: projects do NOT get a SOUL/USER/
MEMORY triplet — confirmed via hermes-agent's own `which-file-does-what.md`
doc, projects get exactly one auto-loaded context file (`.hermes.md` >
`AGENTS.md` > `CLAUDE.md` > `.cursorrules`, first match wins). Created the
project (`p_8e2a7887`, folder `/home/hermes/projects/hermes-install`) and
seeded `AGENTS.md` (4,765/20,000 chars) with infrastructure facts, current
model routing, known gaps, and the full decision history from this
session. Verified live: ran `hermes -z` with cwd set to the project
folder, asked a question only answerable from AGENTS.md, got it right.
Logged as `hermes-install-project-created-2026-10-11`.

The old "Prograder Price Changes" project from before the migration was
not recreated — unrelated to the Hermes-install project, no signal Mark
wants it back.

## What's NOT done yet — pick up here

1. **No real circuit breaker on the fallback path.** Mark's explicit
   requirement (2026-10-07, still unmet): a fallback must not just be a
   bare model pointer — it needs its own rate-limit/circuit-breaker so a
   retry storm can't hammer a **paid** Nous API the way it hung the free
   local Qwen slot during the concurrency crash. **Checked this session:
   no built-in feature for this exists in the current hermes-agent
   version** — only the global `agent.api_max_retries` knob (now set to
   1) and the jittered global retry-storm backoff. A real breaker would
   need either a config feature that doesn't exist yet, or a wrapper
   around the fallback path. Don't consider this solved by the retry
   tuning — it's a partial mitigation only.
2. **Fallback chain is configured but not stress-tested.** We set
   `deepseek/deepseek-v4.1-flash` via Nous as `fallback_providers[0]` and
   confirmed it via `hermes fallback list`, but never actually forced a
   failure on Qwen to watch it fail over live. Worth doing deliberately
   (not via another concurrency crash).
3. **Custom models for other gaps beyond vision** — Mark asked for
   "custom models setup where these ai fall short via
   portal.nousresearch.com" generally, not just vision. Vision is now
   pinned to Nous; audit the other `auxiliary.*` blocks (web_extract,
   compression, title_generation, moa_reference, etc. — see config.yaml
   around line 900+) for whether any of them need the same explicit
   `nous` pin instead of `auto`.

## Why the last session's facts were hard to find (fixed now, but know this)

The Vultr→Nous transition and the Qwen-as-execution-tier decision were
both logged to the catalog same-day as everything else — just in
different vocabulary (`setup_model`/`execution_tier_model` rather than
`fallback`/`provider`). A keyword search for "fallback" or "model" missed
them. This was a **retrieval gap, not a missing-logging gap**. When
reconstructing routing state from the catalog, search broadly (provider
names like `nous`/`vultr`, not just the word "fallback") before treating
any prior routing decision as still current — and always re-verify live
state over a prior session's claimed verification.

## Ground rules reaffirmed/established this session

- **Validate the actually active model, not the config file.** A config
  value matching what you expect is not proof it works — fire a live
  request.
- **Vultr is gone, full stop** — not the VPS (already known), but also as
  an LLM provider. Nous Portal is the sole cloud provider going forward.
- **Mission context, restated by Mark**: Hermes is being set up to fully
  replace Claude Code (CC) as the actual working agent. CC is only the
  bootstrap mechanism used to configure its own replacement — this should
  bias model-routing and capability decisions toward "good enough to
  replace CC," not just "good enough to chat."
