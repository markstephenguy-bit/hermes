# Session Seed — Working with Hermes from Another Device

Paste this whole file as your opening message to pick up where the last
session left off. As of 2026-09-25, the core infrastructure (VPS, Codex,
Docker/Dokploy, WireGuard VPN, Ollama) is built and verified — this
session is about *using* Hermes day to day and finishing the remaining
polish items, not standing up new infrastructure from scratch.

## How to access Hermes right now

- **URL**: `https://0095e5d9-9994-48de-92c1-99f6817c6564.vultropenclaw.com`
- **Two logins required, in order:**
  1. A browser Basic Auth popup (Caddy, the front door) — username `hermes`
  2. Hermes's own app login page — username `hermes`, different password
- **Credentials**: stored in Google Password Manager (user's own choice,
  set 2026-09-25) and in the catalog's encrypted `secrets` table
  (`hermes-vps-caddy-basic-auth`, `hermes-vps-dashboard-basic-auth` —
  needs the vault passphrase, which is never stored anywhere, supplied
  in-chat by the user). Not duplicated here on purpose.
- **Verified 2026-09-25**: this URL is reachable from a Zscaler-managed
  corporate machine (`w_workstation`) — tested directly, got a normal 401
  then a normal 302 through the full auth chain. Zscaler does not block
  it. Bring a personal laptop as backup anyway if paranoid, but it should
  just work from the work computer.

## What's built and verified (2026-09-25)

- **hermes-vps** (207.148.2.224): hermes-agent v0.19.0, Codex
  (`openai-codex`/`gpt-5.6-sol`) is the default provider — Vultr's paid
  Inference API is no longer default. Docker + Dokploy installed (Dokploy
  panel on :3000, localhost-only, reachable via `ssh -L 3000:127.0.0.1:3000
  root@207.148.2.224`). A real firewall now exists on this box (previously
  it had none at all — every port was internet-reachable; fixed, only
  22/80/443/51820 allowed in now).
- **WireGuard VPN** (G4, done): site-to-site tunnel between hermes-vps and
  `server` (192.168.40.250), self-healing via keepalive, no port forwarding
  needed on the home router. Verified: hermes-vps can reach `server`,
  `w_workstation` (192.168.40.100), the catalog API, and Salt's ports
  (4505/4506) all over the tunnel.
- **Ollama on w_workstation**: installed and running as a genuine
  SYSTEM-level Windows service (`OllamaService` scheduled task, no login
  dependency), bound to `0.0.0.0:11434`, firewalled to LAN+tunnel subnets
  only, models stored at `E:\Ollama Models`. Verified reachable from
  hermes-vps over the tunnel. **No models pulled yet** — see below.
- **Squid proxy on `server`** (192.168.40.250:3128): built for a Zscaler
  bypass that turned out not to be needed (the actual fix was trusting
  Zscaler's already-installed root CA, not proxying). Left running,
  restricted to `w_workstation` only, verified working, in case something
  else needs it later.

## Immediate next steps

1. **Pull the local model package into Ollama** (agreed but not yet run):
   - `gpt-oss-20b` (~14GB) — primary model. Chosen over Hermes-4-14B and
     Qwen3-14B specifically because it's benchmarked best for 16GB VRAM +
     agentic tool-calling (MoE, ~140 tok/s, faster than dense alternatives
     at the same footprint). This overrides the earlier "must be Nous's
     Hermes line" preference from BACKLOG.md — a deliberate choice, not an
     oversight.
   - `qwen3-vl:8b` (~12GB) — vision/screenshot understanding. User relies
     heavily on screenshots for context; none of the text-only candidates
     above can see images. Best current OCR/screenshot/UI-understanding
     model available on Ollama.
   - `nomic-embed-text` (~274MB) — better memory/RAG embeddings than
     Hermes's tiny built-in fallback.
   - Note: the 20B and 8B models don't both fit in 16GB VRAM
     simultaneously — Ollama will swap between them on demand. Normal,
     not a bug.
2. **Wire Ollama into Hermes as the fallback/primary provider** (G1/G8,
   not started) — point hermes-vps at `http://192.168.40.100:11434`
   (reachable now over the tunnel) as the preferred provider, Codex as
   fallback when local fails/hits limits. This is the `fallback_providers`
   / MoA mechanism — see Hermes's own docs
   (hermes-agent.nousresearch.com/docs/user-guide/features/fallback-providers).
3. **Personalize `SOUL.md` and `USER.md`** on hermes-vps
   (`/home/hermes/.hermes/`) — both still near-default/empty as of
   2026-09-25. A draft USER.md was worked out in conversation (name,
   location, communication-style preferences, purpose) but never
   committed to the file — check chat history or just re-ask the user.

## Still open on the goals tracker (65/125 points earned)

- G1 (10pts, in_progress): Hermes talking to LM Studio/Ollama — blocked on
  step 2 above.
- G6 (10pts, not started): Hermes Desktop app connected to hermes-vps —
  attempted 2026-09-25, blocked on a version mismatch between the local
  Desktop build and the VPS's v0.19.0 backend (API calls like
  `/api/sessions/owner-backfill` 405, `connectors.list` unknown method).
  Not urgent — the web dashboard is a full substitute.
- G7 (15pts, not started): Signal/Telegram gateway — `hermes-gateway` is
  running, no channel configured yet.
- G8 (15pts, not started): depends on G1.
- G9 (10pts, not started): cancel Claude Pro (keeping ChatGPT Plus +
  Google One).

## Ground rules (apply automatically — do not ask permission for these)

- **Memory and git upkeep are your job, not the user's.** Log
  decisions/facts to the catalog as they happen — tagged `hermes`, atomic
  format (one-sentence `body`, structured `attributes`, `relations` edges
  to connect it to related entities). Commit and push to
  `git@github.com:markstephenguy-bit/hermes.git` as work lands.
- **Everything the user says in conversation is priority** — don't
  silently deprioritize what they're asking about.
- **Secrets never go in this repo or in plain catalog entities.** Real
  credentials go in the catalog's encrypted `secrets` table
  (`POST /rpc/secret_set` / `secret_get`), which requires a passphrase the
  user supplies in-chat each time — it's never stored. The user is also
  now using Google Password Manager for day-to-day credential storage.
- After every catalog write, run `python3 scripts/export_catalog_memory.py`
  from the repo root and commit the resulting `memory/catalog-export.json`.

## Where the full history lives

This file is a snapshot, not the source of truth.
- Full decision history, atomically logged with relations:
  `curl "http://192.168.40.250:3003/entities?tags=cs.%7Bhermes%7D"`
- Goals/points tracker:
  `curl "http://192.168.40.250:3003/entities?type=eq.goal&tags=cs.%7Bhermes%7D"`
- Architecture reasoning: [ARCHITECTURE.md](ARCHITECTURE.md)
- Open questions / non-goals: [BACKLOG.md](BACKLOG.md)
- Repo-specific working conventions: [CLAUDE.md](CLAUDE.md)
