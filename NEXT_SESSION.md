# Session Seed — Hermes Docker on w_workstation: Full Env-Var Configuration Pass

This replaces the previous seed in full — everything below it was from the
VPS/server era and is now stale (Hermes is no longer on the VPS, and the
server-hosted attempt was built, validated, then deliberately torn down in
favor of w_workstation). If you're an agent picking this up cold, read this
whole file before touching anything. If you're Mark pasting this into a new
chat, paste the whole file as your opening message.

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
