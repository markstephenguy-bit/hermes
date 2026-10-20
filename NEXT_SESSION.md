# Session Seed — Hermes Docker on w_workstation: Full Env-Var Configuration Pass

This replaces the previous seed in full — everything below it was from the
VPS/server era and is now stale (Hermes is no longer on the VPS, and the
server-hosted attempt was built, validated, then deliberately torn down in
favor of w_workstation). If you're an agent picking this up cold, read this
whole file before touching anything. If you're Mark pasting this into a new
chat, paste the whole file as your opening message.

## 2026-10-20 update — read this first, it supersedes several items below

A follow-on session picked this up. Mark redirected scope away from the
account-dependent env-var pass (LLM providers, messaging, voice/search APIs —
"those can be put in after hermes comes up") toward what's actually required
for Hermes to function at all, in Docker or anywhere else. Progress:

- **Port-8090 discrepancy resolved, for real this time.** The server was
  never LM Studio's bundled llama.cpp (that's leftover from before Mark
  thought he'd uninstalled it) — it's a standalone build at
  `C:\llama.cpp\llama-server.exe`, serving
  `E:\ik_llama_models\Qwen_Qwen3.5-9B-Q4_K_M.gguf`. It had **crashed on
  2026-10-07** (confirmed via `C:\Users\llm\AppData\Local\CrashDumps\llama-server.exe.24856.dmp`)
  and nobody had restarted it since. Restarted directly via
  `C:\llama.cpp\llama-server.exe -m E:\ik_llama_models\Qwen_Qwen3.5-9B-Q4_K_M.gguf --port 8090 --host 127.0.0.1 --alias Qwen_Qwen3.5_9B -ngl 99 -c 8192`.
  **Important:** launching it via PowerShell `Start-Process -WindowStyle
  Hidden` (detached, redirected to log files) made it die silently within
  ~5s every time, with no crash dump and no error in the log — cause not
  understood. Running it as a normal foreground command over the SSH session
  worked and it kept running independently of the SSH connection
  afterward (session type showed as "Services", not tied to the ssh
  session). If this needs restarting again, start there before assuming
  it's a GPU/model/CUDA problem.
- **Found and fixed a real, separate bug, independent of whether llama-server
  was running:** `config.yaml`'s `providers.local-qwen.base_url` was
  `http://localhost:8090/v1`. That can **never** work once Hermes runs
  inside the Docker container — `localhost` inside a container means the
  container itself, not the Windows host. Confirmed via
  `docker exec hermes curl http://localhost:8090/v1/models` (connection
  refused) vs `docker exec hermes curl http://host.docker.internal:8090/v1/models`
  (succeeds). Fixed to `http://host.docker.internal:8090/v1` in
  `E:\hermes-data\config.yaml`. This means the local-qwen model path was
  broken from the moment Hermes moved into Docker today, regardless of the
  llama-server crash — two separate problems that both needed fixing.
- **Agent Behavior decisions Mark made directly (asked via clarifying
  questions, not assumed):**
  - `HERMES_EXEC_ASK`: left unset/false — **no approval prompts**, despite
    no sandbox isolating Hermes from this host. Mark's call, matches the
    project's turnkey-over-hardening bias; revisit if this bites him.
  - `HERMES_ALLOW_PRIVATE_URLS=true` — Hermes's tools can reach LAN/localhost
    URLs (needed for home-lab integration). This is normally an SSRF-shaped
    surface blocked by default; deliberately opened here.
  - `HERMES_TIMEZONE=America/Chicago` — was unset before (running in
    UTC/system default).
  - Container was recreated (stop/rm/run) with these two new env vars added
    on top of every previously-confirmed env var, same resource limits,
    health check, restart policy, port mappings, and bind mount as before.
- **New, unresolved problem found while testing end-to-end:** after the
  recreate, the container is **crash-looping** — `docker inspect hermes`
  showed `RestartCount=7` within a few minutes of the fresh start.
  `/opt/data/logs/agent.log` shows a repeating ~15s cycle: full plugin
  discovery (55 plugins) → dashboard registration → `agent.credential_pool:
  credential pool: no available entries (all exhausted or empty)` → process
  dies before any chat turn completes. A real end-to-end test (`curl` against
  `API_SERVER` at `192.168.40.100:8642/v1/chat/completions`) got an empty
  reply every time — not because the model is unreachable (confirmed
  reachable separately), but because the whole process keeps dying mid-session.
  **Not yet root-caused.** This directly matches the open question already
  in this file about whether Docker Desktop's all-users/WSL2 setup actually
  survives real-world operation — now there's a concrete data point: it's
  currently not stable even without a logout/reboot in the mix. Pick this up
  first in the next session; nothing else matters if the container can't
  stay up.
- Hindsight (`retain`) returned a 500 mid-session when trying to log this —
  worth a quick health check on `hermes-vps`'s Hindsight instance; per this
  repo's own `CLAUDE.md` it's the sole memory store with no backup yet, so a
  write failure there is itself notable, not just an inconvenience.
- **Crash-loop investigation, continued — hypotheses ruled out one by one:**
  the container restarts every ~15-18s, every time, with `ExitCode=0` and
  `OOMKilled=false` — a clean, deliberate self-exit, not a crash — regardless
  of what's changed:
  - Not the two new env vars (`HERMES_ALLOW_PRIVATE_URLS`,
    `HERMES_TIMEZONE`): recreated without them, loop continued identically
    (confirmed via `container-boot.log`, which persists across recreates on
    the bind mount).
  - Not the `--health-cmd`: recreated with `--no-healthcheck` entirely, loop
    continued at the same cadence (RestartCount climbed 0→1→2 within 40s).
  - Not a stale `gateway_state.json`: it had a dead PID (158) from an earlier
    cycle and hadn't been updated since 03:37, suggesting a stuck handoff —
    deleted it (and `runtime/active_sessions.lock`) with the container
    stopped, restarted clean. Loop continued identically (0→6 within ~70s).
  - Checked Windows Application/System event logs (CrowdStrike runs a
    container-sensor component on this host, `CSFalconContainer.exe`) for
    any correlation with the restart timestamps — found nothing from
    Falcon/CrowdStrike/Docker in the standard event log. Doesn't rule out
    kernel-level EDR intervention that wouldn't surface there, but there's no
    positive evidence for it either. **Do not go looking for ways to work
    around CrowdStrike if this comes up again — Mark has said twice this
    session not to go there; if an EDR correlation is ever found, it's a
    "tell Mark, let him sort it with IT/security" situation, not something to
    engineer around.**
  - `/opt/data/*.lock` files exist but are all 0 bytes (pure existence-marker
    locks); the kanban/state.db ones date to the very first boot (00:53-00:54)
    and don't look actively contended, so didn't pursue clearing those.
  - The container's real work happens as the CMD-as-main-program (Architecture
    B per `/etc/s6-overlay/s6-rc.d/main-hermes/run`'s own comment — the
    `main-hermes` s6 service is an intentional no-op `sleep infinity`
    placeholder, not the actual gateway). The orderly s6 stop/start sequence
    each cycle confirms this is a graceful SIGTERM-driven shutdown of the real
    CMD process, not an unhandled crash — something sends it SIGTERM on a
    very regular cadence, cause still unidentified.
  - **Left the container stopped** (not looping) rather than leave it
    crash-restarting indefinitely while unresolved — `docker start hermes`
    to resume testing. Next session: consider `HERMES_DEBUG_INTERRUPT=1` for
    verbose interrupt/cancel tracing, or comparing against a completely fresh
    bind-mount directory (new `E:\hermes-data-test`) to rule out anything
    specific to this one, heavily-reused data volume after ~30+ rapid
    recreate cycles today.

## RESOLVED — root cause found and fixed (same session, continued)

Mark's instinct to test a completely unconfigured, bare container
(`docker run -d --name hermes-bare nousresearch/hermes-agent:latest`, no env,
no volume, no healthcheck, no restart policy) found it in under two minutes —
it died with the exact same signature (clean exit, ~20s in) as every other
variant, which meant the cause was baked into the image's own default
behavior, not anything either of us had configured.

**The actual bug: every `docker run` all session had left `CMD` empty.**
Reading `/opt/hermes/docker/main-wrapper.sh` directly (`docker run --rm
--entrypoint sh nousresearch/hermes-agent:latest -c "cat
/opt/hermes/docker/main-wrapper.sh"`) shows the routing logic in plain text:

```sh
if [ $# -eq 0 ]; then
    drop hermes
fi
```

With no CMD args, the container's main process is the **interactive `hermes`
chat REPL**, not the gateway daemon. A detached container (`docker run -d`)
has no TTY, so the REPL immediately logs `Warning: Input is not a terminal
(fd=0)`, prints "Shutting down… Goodbye!", and exits cleanly (`ExitCode=0`)
once it finishes its startup banner — which is also exactly why the "crash"
was always ~15-20s in (however long plugin/skill loading + banner rendering
takes) and totally indifferent to env vars, healthcheck config, or
`gateway_state.json`: none of those affect which code path `main-wrapper.sh`
picks. Docker's `--restart unless-stopped` then dutifully relaunched a
process that was never designed to stay open, forever.

**Fix:** pass `gateway run` as the explicit CMD —
`docker run -d --name hermes ... nousresearch/hermes-agent:latest gateway
run`. Confirmed stable for 80+ seconds, `RestartCount=0`, Docker health
status `healthy`, dashboard reachable externally (`curl
192.168.40.100:9119/` → 302).

**Second, smaller bug found immediately after, via the first real end-to-end
test:** a `POST /v1/chat/completions` through `API_SERVER` returned a clean
500 — Hermes enforces a **minimum 64K context window**, but llama-server had
been started with `-c 8192`. Restarted `llama-server.exe` with `-c 65536`
(confirmed via `/v1/models`: `n_ctx: 65536`, ~8.7GB/16GB VRAM, comfortable
headroom), then `docker restart hermes` so it re-probed the model (it had
cached the old 8192 figure from its first boot). **End-to-end chat
completion now succeeds**: `{"content": "pong", ...}`, HTTP 200,
`usage.prompt_tokens: 13441` (full tool/skill system prompt).

This is the first fully working request of the entire session — model
reachable, context adequate, container stable. Current live state to verify
fresh next time, don't assume it survived untouched:
- `hermes` container CMD is `gateway run` (not empty) — if it's ever
  recreated, this is not optional.
- `llama-server.exe` running with `-m E:\ik_llama_models\Qwen_Qwen3.5-9B-Q4_K_M.gguf
  --port 8090 --host 127.0.0.1 --alias Qwen_Qwen3.5_9B -ngl 99 -c 65536`,
  started directly (not via LM Studio), in the foreground over an SSH
  session which then gets backgrounded — this has proven to survive
  independent of the SSH connection (shows up under Windows session type
  "Services"). Has no restart-on-crash wrapper of its own yet; if `w_workstation`
  reboots or the process dies, it needs to be started by hand again until
  that's turned into something more durable (a scheduled task, a Windows
  service, NSSM, etc. — not done this session, worth doing before relying on
  this for real).
- `config.yaml`'s `local-qwen.base_url` is `http://host.docker.internal:8090/v1`
  (not `localhost`) — load-bearing, don't revert.

## Asked again, same session: "what's left to make this complete?"

Checked whether anything in the current stable config was still untested —
it wasn't; everything running together now (dashboard auth, API server,
`SUDO_PASSWORD`, `HERMES_ALLOW_PRIVATE_URLS`, `HERMES_TIMEZONE`, resource
limits, healthcheck, `gateway run` CMD) is the validated, working baseline.
Asked Mark directly about the two items that were actually actionable
(not just "no account, skip" by default) and got explicit "not yet" on both:

- **Telegram** — he confirmed wanting it earlier this session, but when
  asked whether to get the bot token now, said skip it for now too. Not a
  reversal of the earlier "yes" in principle, just not today.
- **Hindsight as Hermes Agent's own memory provider** — would need an SSH
  tunnel from `w_workstation` to `hermes-vps:9177` (Hindsight binds loopback
  there) before `HINDSIGHT_API_URL` could even point at it. Offered to build
  that tunnel now; declined.

Everything else on the original category list (cloud LLM providers,
search/voice APIs, skill keys, Langfuse, Tool Gateway) has no credential
behind it, so there's nothing to add-and-test — "no account, skip" is the
correct final answer for those, not a placeholder. **Current state is as
complete as it can get without new input from Mark.** Next session should
check in on whether any of the above (Telegram token, Hindsight tunnel) has
become actionable, rather than re-deriving this list from scratch.
- Categories deferred per Mark's explicit redirect, not forgotten: LLM cloud
  providers (he mentioned Nous Portal as the eventual target but said it can
  wait), search/voice/tool APIs, all ~17 messaging platforms, Hindsight as
  Hermes's own memory-provider plugin, skill-specific keys, Langfuse
  observability, Nous Tool Gateway. Revisit these only after the container
  stops crash-looping and a chat turn actually completes end-to-end.

## The one job this session exists to do

**Go through every environment variable in Hermes's canonical reference
(`website/docs/reference/environment-variables.md` in
`github.com/NousResearch/hermes-agent`) and make a deliberate, recorded
decision on each one.**

The default posture Mark wants, explicitly stated: **treat every variable as
something that should be set, unless there's a provable reason it doesn't
apply.** "We don't currently use X" is a valid reason to skip a variable —
but it has to be stated, not silently assumed. Don't do a pass that only
touches the ones that feel obviously relevant (dashboard, API server, model
routing) and call it done — that's the mistake the previous session was
explicitly asked not to repeat. Go category by category. For each variable,
record: set / not applicable (why) / deferred (why, and what would change
that). This file is the running checklist — update it in place as you go
rather than starting a parallel doc.

## Current live state — built this session (2026-10-19), verify fresh, don't assume

- **Host:** `w_workstation`, `192.168.40.100` — a Georgia-Pacific/Koch
  **corporate domain-joined Windows 11 laptop** (`bpnet.gapac.com`), not a
  personal box. SSH as `llm` (key `~/.ssh/workstation_llm_ed25519` on Mark's
  laptop), which is a local admin. This machine runs **CrowdStrike Falcon**
  (confirmed, including a container-sensor component,
  `CSFalconContainer.exe`) and **Zscaler**. Mark has explicitly refused twice
  this session to configure anything to evade either — don't suggest it
  again, and don't frame anything as "working around" them.
- **Docker: Docker Desktop**, install mode **all-users**, backend **WSL2**.
  Hyper-V backend was attempted and errored out at install time — not
  diagnosed further, possibly corporate policy blocking it. Don't silently
  retry Hyper-V; if revisiting it, check *why* it errored first.
  - Earlier in this same session, a *raw* `docker.io` engine installed
    directly inside a WSL2 Debian distro (no Docker Desktop) was tried first
    and fully removed — it hit WSL2's "VM tears down shortly after the last
    attached `wsl.exe` client disconnects" behavior, which no amount of
    `vmIdleTimeout` config or scheduled-task keep-alive hackery reliably
    fixed. That's *why* Docker Desktop (all-users/WSL2) is being used instead
    — its own service wrapper manages the VM attachment itself rather than
    relying on an external client process. Per-user install mode was also
    tried first and rejected: it's scoped to whichever Windows account ran
    the installer, and `llm` (the SSH account) couldn't reach its Docker API
    at all. All-users mode fixed that.
- **Container:** name `hermes`, image `nousresearch/hermes-agent:latest`.
  Gateway-only — **no sandbox container**. `terminal.backend: local` in
  `config.yaml`, deliberately, not `docker` — an earlier attempt at the
  Docker-sandboxed terminal backend on this same machine caused enough
  instability ("grief") that gateway-only was chosen instead. Don't
  reintroduce `terminal.backend: docker` / `nousresearch/hermes-sandbox`
  without discussing it first.
- **Data:** bind-mounted at `E:\hermes-data` → `/opt/data` (E: has ~3.78TB
  free vs. C:'s ~64GB; chosen deliberately for space). `config.yaml` has
  `database.journal_mode: "delete"`, not the bundled default `"wal"` — this
  matters specifically because Windows bind mounts into a WSL2-backed
  container cross a virtiofs/9p boundary, which Hermes's own docs say can
  silently corrupt SQLite WAL files. Do not revert this without replacing the
  bind mount with a native Docker volume instead (which would avoid the
  cross-boundary issue a different way, but means relocating Docker Desktop's
  own disk image off C: first — see open item below).
- **Model routing:** `config.yaml` → `model.provider: local-qwen`,
  `providers.local-qwen.base_url: http://localhost:8090/v1` (same machine
  now — Hermes moved to w_workstation, so this is `localhost`, not a remote
  IP). **Discrepancy to resolve first, not assume either way:** every live
  check this session (`netstat`, direct `curl`) found nothing listening on
  port 8090, but Mark's own last message says llama.cpp is running Qwen and
  *is* being used, and that "it should be started." Don't trust either claim
  blindly — check live (`netstat -an | findstr :8090` on the host, plus an
  actual `curl http://localhost:8090/v1/models`) before doing anything else
  model-related, and reconcile what you find against what Mark said.
- **Resource limits applied:** `--memory=8g --cpus=4 --shm-size=1g` (host has
  8 logical cores / ~64GB RAM). Previously had *no* limits at all — Hermes's
  own Docker docs call `--memory`/`--cpus` a minimum-recommended setting
  (stated minimum 4g/2 cpu) specifically to stop runaway browser automation
  from consuming the whole host, and `--shm-size=1g` specifically for
  Playwright/Chromium stability.
- **Health check, restart policy, log rotation:** `--health-cmd="curl -f
  http://localhost:9119/ || exit 1"` (30s interval/start-period, 5s timeout, 3
  retries), `--restart unless-stopped`, `--log-opt max-size=10m --log-opt
  max-file=3`. All confirmed applied via `docker inspect`.
- **Credentials exist already** — don't regenerate them, don't ask Mark for
  them again, pull current values straight from the running container:
  `docker inspect hermes --format '{{.Config.Env}}'` over SSH. Set this
  session: `HERMES_DASHBOARD_BASIC_AUTH_USERNAME`/`_PASSWORD`/`_SECRET`,
  `API_SERVER_KEY`, `SUDO_PASSWORD`. Per Mark's instruction, the same
  password is used for `SUDO_PASSWORD` (the "root" account) and the
  dashboard's `hermes` account; the dashboard secret and API key are
  independently generated (different purpose — cryptographic secrets, not
  login credentials).
- **Ports:** `8642` (API) / `9119` (dashboard), both published and confirmed
  LAN-reachable (`http://192.168.40.100:9119` → `302`). Not yet tested
  for genuine external/internet reachability on this host specifically (that
  whole investigation happened while Hermes was briefly on `server`, see
  below — it doesn't carry over automatically to w_workstation, router
  forwards would need to be re-pointed if internet access here is wanted).

## Decisions from earlier today that should NOT be re-opened without a real reason

- **w_workstation over `server` (192.168.40.250).** Hermes was fully built,
  validated, and working on `server` earlier this same session (clean
  Ubuntu host, no corporate EDR, no WSL2 lifecycle issues) — then Mark
  explicitly tore it down and moved to w_workstation instead once Docker
  Desktop's all-users/WSL2 combination looked like it might solve the
  reliability problem. `server` currently has **zero containers** running
  (verified) and is sitting idle. If w_workstation's reliability doesn't
  actually pan out (worth watching — Docker Desktop's service wrapper is
  *likely* more robust than the raw WSL2 approach was, but this hasn't been
  stress-tested across a real logout/reboot cycle yet), `server` is the
  known-good fallback, not a new idea to propose from scratch.
- **Gateway-only, no sandbox** — see above, don't reintroduce without reason.
- **Basic auth is what's configured for the dashboard.** Hermes's own docs
  are explicit that basic auth is *"intended for trusted LANs or VPN-gated
  access, not direct internet exposure."* If/when this instance is ever
  exposed to the internet (not just LAN), that's a real gap to revisit —
  OAuth/OIDC, not basic auth — but don't silently "fix" it now; it's a
  deliberate deferred item, flag it when internet exposure actually comes up.
- **A separate side-quest about DuckDNS/UFW/CGNAT on `server`/the home
  router happened earlier this session and is unrelated to this task** —
  don't conflate it with w_workstation's networking. That investigation
  confirmed `server`'s Docker/iptables/UFW setup was correct and the failure
  was upstream (router/ISP), never fully resolved (Mark was going to check
  the router's own WAN IP page). It has no bearing on w_workstation.
- **`fileserver` (192.168.40.2) is a separate, unrelated migration target**
  for *other* home-lab services (Plex, WordPress, AdGuard, Portainer,
  Homepage, Beszel-hub, MeshCentral — all explicitly removed from `server`
  today with the intent of reinstalling fresh on `fileserver`, no backups,
  per Mark's instruction). That migration hasn't started yet and is not
  this session's job unless Mark asks for it specifically.

## The actual checklist — canonical env-var categories

Source: `github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/environment-variables.md`
(~900 lines, re-fetch it fresh rather than trusting this summary blindly —
it may have changed). Categories already given real attention this session
(see state above) vs. categories that still need the full one-by-one pass:

**Already decided, don't redo from scratch — just verify still correct:**
- Configuration & Runtime (`HERMES_HOME`, `database.journal_mode`, etc.)
- Terminal & Sandbox Backends (`TERMINAL_ENV=local`, `SUDO_PASSWORD` set)
- Container Resources (`TERMINAL_CONTAINER_*` — note: these govern the
  *sandbox* container's resources, which doesn't apply here since
  `terminal.backend` isn't `docker` — confirm this is correctly a no-op, not
  silently misapplied)
- Persistent Shell (`TERMINAL_PERSISTENT_SHELL` etc. — defaults are `true`,
  check if that's actually desired or needs an explicit override)
- Dashboard Authentication (basic auth configured; OIDC/OAuth variables
  deliberately unset — see "don't re-open" above)
- Gateway Configuration (`GATEWAY_ALLOW_ALL_USERS` etc. — currently unset;
  only matters once messaging platforms are configured, which they aren't)
- Messaging: Webhook & API Server (`API_SERVER_*` set; `WEBHOOK_*` unset —
  no webhook consumer configured, confirm that's still the right call)

**Needs the full deliberate pass, not yet done:**
- LLM Providers (all the cloud-provider keys — `OPENROUTER_API_KEY`,
  `OPENAI_API_KEY`, `FIREWORKS_API_KEY`, `NOUS_BASE_URL`/`NOUS_INFERENCE_BASE_URL`,
  `COPILOT_GITHUB_TOKEN`, `GLM_API_KEY`, etc. For each: does Mark have an
  account for it? If not, that's the "proven reason to skip" — record it,
  don't just leave it silently unset.)
- Voice & Speech Tools (`ELEVENLABS_API_KEY`, `GROQ_API_KEY` for Whisper STT,
  `PORCUPINE_ACCESS_KEY`, etc.)
- Tool & Web APIs (search: `TAVILY_API_KEY`, `PERPLEXITY_API_KEY`,
  `BRAVE_SEARCH_API_KEY`, `EXA_API_KEY`; browser: `BROWSERBASE_API_KEY`,
  `BROWSER_CDP_URL`; image gen: `FAL_KEY`, `KREA_API_KEY`)
- Integrations (`HINDSIGHT_API_KEY`/`HINDSIGHT_API_URL` — note Hindsight is
  explicitly the project's real memory system per the repo's own `CLAUDE.md`,
  so this one deserves real attention, not a quick skip; also `MEM0_*`,
  `HONCHO_*`, `DAYTONA_API_KEY`, `VERCEL_TOKEN`)
- Skill-Specific API Keys (`NOTION_API_KEY`, `LINEAR_API_KEY`,
  `AIRTABLE_API_KEY`, `TENOR_API_KEY`)
- Observability/Langfuse (`HERMES_LANGFUSE_*` — likely a real "no account,
  skip" unless Mark wants call-tracing observability)
- Tool Gateway (`TOOL_GATEWAY_*`)
- Agent Behavior (`HERMES_MAX_ITERATIONS`, `HERMES_YOLO_MODE`,
  `HERMES_SAFE_MODE`, etc. — worth a deliberate choice, not defaults by
  accident)
- All ~17 messaging platform sections (Telegram, Discord, Slack, Google Chat,
  WhatsApp, Signal, SMS/Twilio, Email, DingTalk, Feishu, WeCom, Weixin,
  BlueBubbles, QQ, Mattermost, Matrix, Home Assistant, Teams, LINE, ntfy,
  IRC, SimpleX, Photon, Buzz/Nostr, Raft) — each follows the same
  `HOME_CHANNEL`/`HOME_CHANNEL_NAME`/credential pattern. Go through each one:
  does an account/bot/channel actually exist for it? The honest expectation
  is most will be "no account, skip" — but that has to be checked and stated
  per platform, not assumed as a block.

## Open items, not blocking, pick up if relevant

- Docker Desktop's own disk image (container layers/image cache, separate
  from Hermes's `/opt/data`) is still on C:, not E:. Relocating it is a
  built-in Docker Desktop feature (Settings → Resources → Advanced → Disk
  image location) — safer done via that GUI action than by hand-editing
  files, deliberately not attempted yet.
- Whether Docker Desktop's all-users/WSL2 setup actually survives a real
  logout or reboot (not just idling) hasn't been stress-tested — that's the
  whole point of this detour from the raw-engine approach, worth actually
  checking rather than assuming it's fixed.
