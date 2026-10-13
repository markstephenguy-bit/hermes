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

### Responsiveness & compression fast-lane tuning (deployed 2026-10-13 02:10 UTC)

Mark ran an optimize sweep on `/home/hermes/.hermes/config.yaml` (`compression.threshold: 0.45`, `target_ratio: 0.25`, `protect_last_n: 12`, `protect_first_n: 2`, `proactive_prune_min_result_chars: 10000`, `session_cleanup`, `agent.cache`, `delegation`, `curator`) and reported that the context-summarize (`compression`) thread still took ~191 seconds (`01:48:29`–`01:51:41` UTC).

Root cause of the 191.5s summarize stall (`agent.log` attempt `edb0af5f98aa4a549eaf29585ccca883`):
1. `auxiliary.compression` was still on `provider: auto` (routing to local `w_workstation:8090` `Qwen_Qwen3.5-9B-Q4_K_M.gguf`). Unlike the main agent loop (which hits 95–100% KV-cache reuse on Slot 0), the compression prompt has **0% KV-cache overlap** (`7,143` uncached prompt tokens) and contended with Hindsight's background `consolidation` worker on the single RTX 5060 Ti, stalling mid-stream for 60.0s (`96.5s` total) before timing out.
2. When it fell back to `fallback_providers[0](nous)` (`deepseek/deepseek-v4.1-flash`), `reasoning_effort: none` was not set, so `deepseek/deepseek-v4.1-flash` spent another `94.0s` generating reasoning tokens (`190,814ms` total).

Deployed fixes (all user optimize-sweep settings preserved intact):
- **`auxiliary.compression` pinned to certified Nous Fast Lane:** `provider: nous`, `model: deepseek/deepseek-v4.1-flash`, `reasoning_effort: none` (plus `reasoning_effort: none` across all auxiliary tasks and `extra_body: {chat_template_kwargs: {enable_thinking: false}}` on local-routed auxiliary tasks). Verified live via `resolve_compression_fast_lane()` (`certified_non_reasoning=True`): a 27,000-char (`~7,000` token) compression window now completes in **2.66–3.49 seconds** (`len_reasoning=0`) and never touches or evicts the local `w_workstation:8090` KV cache.
- **Hindsight non-thinking & low-budget tuning:** `~/.hindsight/profiles/hermes.env` and `~/.hermes/hindsight/config.json` now run with `HINDSIGHT_API_LLM_EXTRA_BODY={"chat_template_kwargs": {"enable_thinking": false}}`, `HINDSIGHT_API_LLM_REASONING_EFFORT=none`, `HINDSIGHT_API_LLM_MAX_CONCURRENT=1`, `recall_budget: low`.
- **VPS headroom & observability:** Added persistent 4 GiB `/swapfile` on `hermes-vps`, set `Restart=always` (`RestartSec=5`) on `hermes-dashboard.service`, and installed `/usr/local/bin/hermes-status` (on VPS host and inside Docker sandbox) to inspect VPS RAM/swap, active `hermes` processes, `w_workstation:8090` GPU slot utilization, and recent turn/compression latencies. Full details in catalog entities `hermes-resource-and-compression-tuning-2026-10-12` and `hermes-vps-compression-fast-lane-2026-10-12`.

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
- **Sandbox isolation & controlled SSH access to the VPS host (`hermes@31.220.53.141`).**
  The `code_execution`/`terminal` sandbox is a separate Docker container
  (`nousresearch/hermes-sandbox:desktop`) without direct bind-mounts of
  `~/.hermes/` (direct bind-mounts caused `root:root` `CAP_DAC_OVERRIDE` file
  ownership corruption on `config.yaml`/`.env`/`auth.json` on 2026-10-08).
  - Forwarded `HERMES_LOCAL_MODEL_BASE_URL` / `HERMES_LOCAL_MODEL_NAME` into
    the sandbox via `terminal.docker_forward_env` in `config.yaml`.
  - **Added 2026-10-12:** Provisioned an `ed25519` SSH keypair in the persistent
    sandbox home (`/home/hermes/.hermes/sandboxes/docker/default/home/.ssh/id_ed25519`,
    mounted at `/root/.ssh/id_ed25519` inside the container) and authorized it
    in `/home/hermes/.ssh/authorized_keys` (UID 1000 `hermes`, **not** `root`,
    preventing `root:root` ownership hazards). Configured sandbox `~/.ssh/config`
    and `/usr/local/bin/ssh` wrapper so `ssh 31.220.53.141`, `ssh hermes@31.220.53.141`,
    and even `ssh root@31.220.53.141` automatically log in as `hermes@31.220.53.141`
    with `hermes`/`uv`/`uvx`/`node`/`npm` and `XDG_RUNTIME_DIR=/run/user/1000`
    in non-interactive `PATH`.
  - **`hermes-doctor-watch`** (`systemd --user` timer, every 6h) also runs
    `hermes doctor` automatically on the host and Telegram-alerts Mark only on
    new or resolved warnings vs. baseline.
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
- **Root cause 5 (Recall budget & CPU cross-encoder tuning as bank grew to 216+ facts):**
  When the bank was empty, synchronous recall over `"observation,world,experience"` with `budget: "mid"` (`max_tokens: 4096`) took 0.20s. Once the bank reached 216+ facts, scoring 216–223 candidates through the local CPU cross-encoder on 2 vCPUs took **16.85s** (exceeding Hermes's 8.0s prefetch timeout) and injected **4,092 tokens (96 facts)** per turn. Updated `~/.hermes/hindsight/config.json` to `"recall_budget": "low"`, `"recall_max_tokens": 1024`, `"recall_types": "observation"` (Hindsight's consolidated layer), and `"recall_sync": false` (async prefetch between turns), cutting recall time to **5.56s** off the critical reply path.
- **Deployment remains self-contained:** `local_embedded`, API loopback
  `127.0.0.1:9177`, embedded Postgres under
  `~/.pg0/instances/hindsight-embed-hermes`, local embedding/reranking models.
  Only inference uses `w_workstation:8090`, matching the active Qwen3.5-9B.
- **Evidence:** verified live with an ordinary `hermes -z` conversation turn (no
  explicit memory tool calls): automatic `batch_retain` extracted and stored the
  fact in 4.35s, consolidation completed in 4.90s, and recall was verified live.
- **Built-in memory remains complementary:** MEMORY.md and USER.md still
  exist and were not reset. The dashboard deliberately displays them
  alongside Hindsight.

## Resource & Responsiveness Tuning — 2026-10-12

- **Fixed 4–8 minute turn stalls caused by local `context_compressor` `<think>` generation:**
  `agent/context_compressor.py` called `w_workstation:8090` (`Qwen_Qwen3.5-9B-Q4_K_M.gguf`) without `enable_thinking: false` and with uncapped `max_tokens`, spending **239–515s (4–8.5 minutes)** generating 6,000–15,000 `<think>` tokens that `strip_think_blocks()` immediately discarded. Added `extra_body: {chat_template_kwargs: {enable_thinking: false}}` to all local Qwen auxiliary tasks (`compression`, `title_generation`, `skills_hub`, `mcp`, `voice_chat`, `profile_describer`, `curator`). Live compression call latency dropped to **1.28s**.
- **Fixed compression re-triggering on every turn (`protect_last_n: 20` -> `8`):**
  With 11 active MCP servers injecting ~35,000–39,000 tokens of tool schemas into every turn out of the 64,000-token slot context (`threshold: 0.5` = `54,400` tokens), `protect_last_n: 20` (~14,000 tokens) left post-compression prompts at ~44,000–50,350 tokens — re-triggering compression every 1–2 turns. Lowered `compression.protect_last_n` to `8` and `protect_first_n` to `1`.
- **Fixed `auxiliary.background_review` and `nous`-pinned auxiliary tasks:**
  Hermes Desktop's UI saved `auxiliary.review: {provider: nous}`, whereas `agent/background_review.py` reads `auxiliary.background_review` AND requires both `provider` and `model` (otherwise silently falling back to the main local GPU and running a 50k-token review fork + compression after every turn). Additionally, `agent/auxiliary_client.py` (`resolve_provider_client`) pre-filled `model` from `model.default` (`E:\ik_llama_models\Qwen_Qwen3.5-9B-Q4_K_M.gguf`) whenever a non-vision `nous` task omitted `model`. Explicitly pinned `model: deepseek/deepseek-v4.1-flash` on `approval`, `review`, `background_review`, `triage_specifier`, and `kanban_decomposer`, and `model: google/gemini-3.8-flash` on `vision`.
- **VPS swap & live resource visibility (`/usr/local/bin/hermes-status`):**
  Killed 1.1 GiB of orphaned `agent-browser` / headless Chromium processes, provisioned a persistent **4 GiB `/swapfile`** in `/etc/fstab` (was `0B` swap on 7.8 GiB RAM), and installed `/usr/local/bin/hermes-status` on both `hermes-vps` and inside the Docker sandbox containers so resource/GPU-slot utilization can be inspected anytime from SSH or Hermes Desktop chat.

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
- **MCP servers configured (2026-10-12):** `linear` and `notion` (OAuth
  authenticated and connected), plus `aws-knowledge`, `context7`, `wolfram`,
  `deepwiki`, `microsoft-learn`, `twilio-docs`, `trivago`, `kiwi`, and
  `alltrails`. `gitlab` (`https://gitlab.com/api/v4/mcp`) was set to
  `enabled: false` after GitLab returned `403 Forbidden - MCP server not enabled
  for any of your groups` (GitLab Duo group-level requirement; misreported by
  `humanize_oauth_registration_error` as a DCR 403).
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
- Vision (`auxiliary.vision`) is now pinned to `provider: nous`, `model: google/gemini-3.8-flash` (fixing the earlier intermittent fallback where an unset `model` let `get_text_auxiliary_client("vision")` pre-fill the local text-only Qwen GGUF path).
- The local browser is still blocked. The managed Chromium binary was found
  and its missing Ubuntu runtime libraries installed, but its normal sandbox
  cannot start under the VPS's AppArmor user-namespace restriction. A proposed
  unconfined AppArmor profile was rejected by automatic approval review for
  weakening a host security boundary; no policy bypass was applied.
- `computer_use` is enabled in the tool list, but `hermes computer-use status`
  reports `cua-driver: not installed` on this headless VPS.
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
