# Session Seed — Hostinger VPS, Hindsight Memory, Self-Monitoring

This is the single most current record of infrastructure state for this
project — more current than ARCHITECTURE.md/BACKLOG.md. If you're an agent
(Claude Code, Codex, Antigravity, or otherwise) picking this project up cold,
read this file in full before touching anything. If you're a human in a chat
UI, paste this whole file as your opening message instead. Full detail and
reasoning for everything below is in the catalog (`curl
"http://192.168.40.2:3003/entities?tags=cs.%7Bhermes%7D"` — search broadly,
not just by the word you expect) — this file is a pointer, not the archive.

## The one rule that mattered most this session

**The chat agent will claim success even when the underlying tool call
failed.** Caught twice tonight:
1. Asked to benchmark tokens/sec — wrote a placeholder script instead of
   running a real test, presented it as a deliverable.
2. Asked to retain a memory via Hindsight — replied "Stored in memory" while
   the server logs showed `RuntimeError: Failed to start the Hindsight
   daemon` underneath.

**Never trust the chat response alone for anything that touches a real
system.** Check the actual log/process/file state. Both of tonight's
failures were real, fixable infra gaps (missing env vars, missing `PATH`
entry) — not reasoning failures — but the agent reported them as done
regardless.

## Current state — re-verified live 2026-10-12, not assumed

- **VPS**: Hostinger KVM 2, `srv2051520.hstgr.cloud`, `31.220.53.141`. SSH as
  `root` (key: default `~/.ssh/id_ed25519`). **Vultr is gone, full stop** —
  destroyed 2026-10-10, not the host, not an LLM provider. Don't reference it.
- **Self-sufficiency rule (hard)**: hermes-vps must work fully even if
  fileserver/WireGuard/home-network is unreachable. The *only* sanctioned
  local-network dependency is the LLM tier itself — `w_workstation`
  (192.168.40.100:8090, `ik_llama.cpp`, OpenAI-compatible, no auth) as
  primary, Nous Portal (`deepseek-v4.1-flash`) as cloud fallback, auto-
  engaging only on technical failure, never on preference. This is NOT just
  "avoid depending on home network for convenience" — Mark was explicit that
  WireGuard dropping must not degrade anything except that one LLM tier.
- **Local model swapped tonight**: Qwen3.6-35B-A3B → `Qwen_Qwen3.5-9B-Q4_K_M`.
  Check `config.yaml`'s `model.default` for whatever it is *now* — it will
  keep changing. Verified live at 53.6 tok/s (direct curl) and 23–75 tps
  (agent's own tool-based benchmark, after the sandbox fix below).
  **This model name is now duplicated in 3 places that must be kept in sync
  by hand whenever it's swapped again:**
  1. `config.yaml` → `model.default` / `model.base_url`
  2. `~/.hermes/hindsight/config.json` + `~/.hindsight/profiles/hermes.env`
     → `llm_model` / `HINDSIGHT_API_LLM_MODEL`
  3. `~/.hermes/.env` → `HERMES_LOCAL_MODEL_BASE_URL` / `HERMES_LOCAL_MODEL_NAME`
- **Dashboard** (`https://theguylab.duckdns.org`) is now double-gated:
  - Caddy `basic_auth` (user `mark`) in front — unchanged, existing.
  - Hermes's **own** `dashboard.basic_auth` (user `mark`, new password
    generated tonight) — required because setting `HERMES_DASHBOARD_PUBLIC_URL`
    (needed to fix a WS `origin_mismatch` reconnect loop) makes Hermes refuse
    to bind at all without its own auth provider configured. First attempt at
    the public_url fix alone crash-looped the dashboard service 40+ times —
    both pieces are needed together or it's broken one way or the other.
  - **New password is only in tonight's chat log, NOT vaulted** —
    `mcp__vault__set_secret` needs Mark's vault passcode, which this session
    didn't have. Get it from Mark and vault it as a correction to
    `hermes-vps-dashboard-basic-auth`.
  - **Mark has not yet confirmed in his own browser** that login + live
    chat/websocket actually works end-to-end post-fix. Ask him, or test it
    yourself if you have a way to drive a real browser session.
- **Sandbox isolation (`code_execution`/`terminal` tools) is by design, not
  a bug.** It's a separate Docker container (`nousresearch/hermes-sandbox:desktop`)
  with no mount of `~/.hermes/`, no config, bare env. It genuinely cannot run
  `hermes doctor`, read `config.yaml`, or self-administer — that's a security
  boundary (don't let the LLM freely execute against its own privileged
  install). Network egress to the LAN *does* work fine from inside it
  (verified directly). Fixed tonight: forwarded `HERMES_LOCAL_MODEL_BASE_URL`
  / `HERMES_LOCAL_MODEL_NAME` into the sandbox via `terminal.docker_forward_env`
  in `config.yaml`, so tool calls can now self-benchmark without guessing.
- **`hermes doctor` cannot be run by the chat agent on itself, ever** (same
  sandbox reason). Don't ask it to, and don't send Mark hunting for the
  dashboard's "Run doctor" button either — he doesn't know the UI and
  shouldn't have to be the manual trigger. Instead: **`hermes-doctor-watch`**,
  a new `systemd --user` timer (every 6h, linger already on, survives
  reboot), runs `hermes doctor` directly on the host and Telegram-alerts
  Mark only on *new or resolved* warnings vs. the last run — no repeat noise
  for the ~18 known/harmless baseline items (npm lockfile advisories,
  unconfigured optional providers like Discord/xAI).
- **MEMORY.md / USER.md were wiped again**, separately from the
  Vultr→Hostinger migration wipe already documented from 2026-10-11. This
  time it happened during tonight's Hindsight plugin install/restart window
  (directory mtime lines up exactly); **the actual deletion mechanism was
  never found** — no log line anywhere shows it, no backup existed. Rewrote
  both from scratch (same method as before: Claude Code's own knowledge +
  catalog cross-check), verified live via fresh `hermes -z` round trip.
  Current sizes: `USER.md` 1,039/1,375 chars, `MEMORY.md` 1,297/2,200 chars.
  **If they go missing a third time, that's a real pattern worth root-causing
  properly instead of just rewriting again.**

## Long-term memory provider: Hindsight — fully repaired & verified (explicit + automatic retain/recall)

Direct VPS repair and verification completed 2026-10-12 (~15:12 UTC). The plugin's
`ready` dashboard badge only checks configuration/client imports; do not use it
as evidence of successful memory operations.

- **Root cause 1 (missing dummy API key):** the daemon's own log
  (`~/.hindsight/profiles/hermes.log`, distinct from Hermes's
  `~/.hermes/logs/hindsight-embed.log`) showed a fatal missing
  `HINDSIGHT_API_LLM_API_KEY`. The local model requires no authentication, but
  Hindsight requires a nonempty value. Set the non-secret placeholder
  `local-no-auth` in `hindsight/config.json` (`llm_api_key`) and the profile env.
- **Root cause 2 (profile `.env` drift restart loop):** the daemon adds
  `HINDSIGHT_API_PORT` to its profile env. The plugin compared the entire file
  against its own settings, so each new plugin instance treated port metadata as
  drift and restarted the daemon, interrupting writes with HTTP 500. Also,
  `_materialize_embedded_profile_env` previously overwrote `hermes.env` with only
  6 hardcoded keys, wiping any custom `HINDSIGHT_API_*` tuning on model swaps.
  Patched `~/.hermes/plugins/hindsight/__init__.py` and `embedded.py` to compare
  only Hermes-owned settings, forward `llm_reasoning_effort` / `llm_extra_body` /
  `llm_max_concurrent` / `llm_max_retries` / `llm_timeout` from `config.json`,
  and preserve existing keys when rewriting `hermes.env`. Recoverable patch:
  `patches/hindsight-profile-restart.patch` (apply inside
  `~/.hermes/plugins/hindsight` with `patch -p1`). Original backups remain with
  `.before-20261012-repair` suffixes.
- **Root cause 3 (`Qwen3.5-9B` `<think>` mode causing 120s extraction timeouts):**
  `ik_llama.cpp` on `w_workstation:8090` defaults Qwen3.5's chat template to
  `<|im_start|>assistant\n<think>\n` with `max_tokens: 64000`. On Hindsight's
  ~3.5k-token `retain_extract_facts` prompt, Qwen3.5-9B generated 4,000–5,000+
  `<think>` tokens before emitting JSON — making single-fact retains take 98s and
  ordinary automatic chat retains exceed the 120s timeout on all 4 attempts
  (locking up `w_workstation` slots for 8+ minutes per turn and failing to save).
  Set `llm_reasoning_effort: "none"`,
  `llm_extra_body: {"chat_template_kwargs": {"enable_thinking": false}}`,
  `llm_max_concurrent: 1`, and `llm_max_retries: 2` in
  `~/.hermes/hindsight/config.json` (and `~/.hindsight/profiles/hermes.env`).
  **Result:** automatic chat fact extraction dropped from **>480s timeout** to
  **4.35s**, and consolidation dropped from **15.4s** to **4.90s**.
- **Root cause 4 (`Command not found: uvx` in dashboard / isolated sessions):**
  `uv` and `uvx` were only symlinked in `/home/hermes/.local/bin`, which was in
  `hermes-gateway.service`'s `PATH` but missing from `hermes-dashboard.service`
  and `tui_gateway` child environments. Symlinked `uv` and `uvx` into
  `/usr/local/bin` and added the full `Environment="PATH=..."` to
  `hermes-dashboard.service`.
- **Root cause 5 (Turn 1 blind spot & observation-only filter on recall):**
  `recall_sync` defaulted to `false` (designed for slow cloud APIs), which meant
  Turn 1 of any new session (`hermes -z`, Telegram, dashboard) injected zero
  recalled memories and Turn 2 injected memories matched against Turn 1's query.
  `recall_types` also defaulted to `"observation"` only, hiding newly retained
  `world`/`experience` facts until background consolidation finished. Because
  local embedded recall takes only **0.20–0.33s**, set `"recall_sync": true` and
  `"recall_types": "observation,world,experience"` in
  `~/.hermes/hindsight/config.json`.
- **Deployment remains self-contained:** `local_embedded`, API loopback
  `127.0.0.1:9177`, embedded Postgres under
  `~/.pg0/instances/hindsight-embed-hermes`, local embedding/reranking models.
  Only inference uses `w_workstation:8090`, matching the active Qwen3.5-9B.
- **Evidence:** verified live with an ordinary `hermes -z` conversation turn (no
  explicit memory tool calls): automatic `batch_retain` extracted and stored the
  fact in 4.35s, consolidation completed in 4.90s, and a subsequent fresh
  single-turn `hermes -z` session recalled the exact fact on Turn 1 in 0.20s
  before test artifacts were cleaned up via `DELETE /documents/{id}`.
- **Built-in memory remains complementary:** MEMORY.md and USER.md still
  exist and were not reset. The dashboard deliberately displays them
  alongside Hindsight.

## Configuration audit — 2026-10-12

- Local model endpoint, Nous login/fallback pointer, Telegram polling,
  gateway, dashboard, and public Caddy authentication challenge all check out.
  The doctor timer is enabled. The public dashboard's two-auth browser flow
  has not been verified end to end; the new inner password is still not in
  the vault (see dashboard note above).
- Fallback has no dedicated circuit breaker or deliberate failure test. This
  matters most before trusting automatic paid failover under local outages.
- Gateway warns that Docker has no host-visible output mount, so files created
  inside `/workspace` or `/output` may fail as Telegram attachments. Sandbox
  isolation itself is intentional; resolve media delivery with a narrow
  output path rather than mounting the whole Hermes home.
- `hermes doctor --live` reports Playwright missing, but that probe does not
  diagnose the active browser runtime. A fresh direct launch on 2026-10-12
  found missing Chromium libraries (installed) and then Ubuntu AppArmor's
  user-namespace restriction. The managed browser remains unavailable; see
  the selected-plugin audit below.
- No MCP servers or Hermes cron jobs are configured. This is inventory, not a
  defect by itself: the catalog tool is available through Hermes's toolset,
  and the separate doctor systemd timer already runs.
- The doctor's three reported npm dependency advisories (browser runtime,
  web build workspace, TUI build workspace) are upstream lockfile issues; a
  local `npm audit fix` would be overwritten by the next Hermes update.
- Optional OpenRouter, Codex, xAI, MiniMax, Discord and similar integrations
  are unset. They are not required for the currently selected local + Nous
  model path. Skills Hub is uninitialized and `GITHUB_TOKEN` is unset, which
  matters only if Hermes should use that hub heavily (60 requests/hour
  unauthenticated GitHub limit).

## Selected-plugin live audit — 2026-10-12

- Verified actual tool calls, not just plugin badges: `web_search`,
  `web_extract`, Krea image generation, and Nous text-to-speech returned usable
  results. The TTS default Edge route failed with HTTP 403; live
  `~/.hermes/config.yaml` now has `tts.provider: nous`, and a test generated a
  valid MP3. Telegram bot identity and gateway polling, Hindsight health,
  local-model chat, a direct request to the configured Nous fallback model,
  and the dashboard's authentication challenge also passed.
- Vision described a generated image correctly on one `vision_analyze` call,
  but a repeat call reached the text-only local Qwen endpoint and failed with
  `image input is not supported` (HTTP 500). `auxiliary.vision.provider: nous`
  is configured; routing remains intermittent and needs a targeted fix.
- The local browser is still blocked. The managed Chromium binary was found
  and its missing Ubuntu runtime libraries installed, but its normal sandbox
  cannot start under the VPS's AppArmor user-namespace restriction. A proposed
  unconfined AppArmor profile was rejected by automatic approval review for
  weakening a host security boundary; no policy bypass was applied.
- `computer_use` is enabled in the tool list, but `hermes computer-use status`
  reports `cua-driver: not installed` on this headless VPS. No MCP servers or
  Hermes cron jobs are configured. These are inventory, not failures of the
  selected Telegram/web/memory workflow.
- Fallback endpoint availability was tested directly; automatic failover
  during a local-model outage remains untested. TTS output exists on the host,
  but Telegram audio attachment delivery was not tested. The separate tool
  sandbox cannot read `~/.hermes/cache/audio`, as expected from its isolation.

## Carried over, untouched tonight (from 2026-10-10/11 sessions)

1. **No real circuit breaker on the fallback path.** Only the global
   `agent.api_max_retries` (=1) and jittered retry-storm backoff exist — no
   actual rate-limit/circuit-breaker to stop a retry storm hammering the
   *paid* Nous API. No built-in hermes-agent feature for this; would need a
   wrapper.
2. **Fallback chain configured but never stress-tested** — `deepseek-v4.1-flash`
   via Nous is `fallback_providers[0]`, confirmed via `hermes fallback list`,
   but no one has deliberately forced a Qwen failure to watch it fail over.
3. **Audit remaining `auxiliary.*` blocks** (web_extract, compression,
   title_generation, moa_reference, etc.) for whether any need an explicit
   `nous` pin like `vision` got, instead of `auto`.

## Ground rules reaffirmed/added this session

- **Verify server/process/file state, not the chat response** — see top of
  this file. This is now the single most important lesson from tonight.
- **Hermes-first, not Mark-as-go-between.** Before telling Mark to click
  something in a UI he doesn't know, ask whether Claude Code already has
  direct access (SSH, API) to just do it, or whether this is a recurring
  need that should become a standing Hermes capability (cron/timer) instead
  of a one-off manual trigger.
- **Sandbox isolation from the real install is intentional** — don't treat
  it as a bug to "fix" by mounting config/cwd in without discussing the
  security tradeoff with Mark first (`docker_mount_cwd_to_workspace` is off
  by default for exactly this reason).
- **Validate the actually active model, not the config file** — fire a live
  request after any `config.yaml` change, don't just string-match.
- **Mission context, restated by Mark**: Hermes is being set up to fully
  replace Claude Code as the actual working agent. CC is only the bootstrap
  mechanism configuring its own replacement.
