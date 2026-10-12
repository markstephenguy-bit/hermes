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

## Long-term memory provider: Hindsight — UNCONFIRMED, pick up here first

Decision (2026-10-04, re-affirmed tonight): **Hindsight**, `local_embedded`
mode (own process + embedded Postgres, no Docker — a separate `hindsight-api`
binary via `uvx`, not a container). Configured to use the same local-model
endpoint as the main chat model, per Mark's instruction to track "whatever
the default profile is."

**What actually happened tonight, in order:**
1. First retain attempt: chat replied "Stored" — **actually failed**
   server-side. Root cause: `uv`/`uvx` were installed
   (`~/.hermes/tools/uv-0.12.3-linux-x64/`) but not on the `hermes` user's
   `PATH`, so the embedded daemon's `uvx hindsight-api@0.10.3` launch command
   failed with "command not found."
2. Fixed: symlinked `uv`/`uvx` into `~/.local/bin` (already on `PATH`).
3. Second retain attempt: the real `hindsight-api` process **did** start,
   pulled ~6.5GB of embedding-model dependencies into `~/.cache/uv`, ran for
   several minutes using real CPU/memory — then **disappeared** without
   logging success or failure to `~/.hermes/logs/hindsight-embed.log`, and
   `~/.pg0/instances/` (where its embedded Postgres would live) was **never
   created**. No OOM-kill evidence in `dmesg`/`journalctl -k` for that window,
   but not conclusively ruled out either (VPS has 8GB RAM, ~5.9GB was free
   at the time).

**Status at session end: genuinely unknown whether Hindsight works.** Do not
assume it does because the plugin shows `active` in `hermes memory status`
— that only means it's configured, not that retain/recall actually succeed.

**Next steps, in order:**
1. `hermes -z "Use your memory tool to retain this fact: <new unique
   marker>. Confirm you stored it."` then immediately check, don't trust the
   reply: `ps aux | grep hindsight-api`, `ss -tlnp | grep -E '8888|9177'`,
   `ls ~/.pg0/instances/`, and the tail of
   `~/.hermes/logs/hindsight-embed.log` for an actual success/failure line.
2. If it dies again mid-startup with no logged reason, check
   `journalctl -k` more broadly (wider time window) for OOM, and consider
   whether the 8GB VPS is simply too tight for Hindsight's embedding stack
   alongside the gateway/dashboard/sandbox already running — may need to
   test on a bigger box or look at Hindsight's lighter-weight modes.
3. Only once a retain+recall round trip is confirmed via process/file state
   (not chat text) should this be marked actually working.

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
