# Session Seed — Hermes Default Profile, Post-Outage

Paste this whole file as your opening message.

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
