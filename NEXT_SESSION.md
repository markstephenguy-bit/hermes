# Session Seed — Get Hermes Working on the VPS (Codex-first)

Paste this whole file as your opening message to start a focused session on
exactly one thing: getting Hermes fully operational on the already-running
VPS using OpenAI Codex/ChatGPT Plus. **Local network, LM Studio, and any
VPN/tunnel work are explicitly out of scope for this session** — that's a
later phase, don't touch it, don't discuss it unless the user brings it up
first.

## Current state (as of 2026-09-24)

- **VPS**: Vultr "High Performance AMD", Dallas TX. IP `207.148.2.224`,
  hostname `hermes-vps`. Official Nous Research `HermesAgent` Ubuntu 24.04
  marketplace image. $24/mo + $4.80/mo backups.
- **Credentials**: root password lives in the Vultr console only
  (console.vultr.com) — not in this repo, not in the catalog. If you need
  it, ask the user; don't assume a stored one is still valid (it was
  rotated at least once already after being shown in a screenshot).
- **Public URL**: `https://0095e5d9-9994-48de-92c1-99f6817c6564.vultropenclaw.com`
  — Caddy is already configured with auto-TLS (Let's Encrypt/ZeroSSL) and
  HTTP Basic Auth in front of the dashboard. This part is done, don't rebuild it.
- **Services**: `hermes-dashboard.service` (port 9119) and
  `hermes-gateway.service`, both active via systemd.
- **Version**: was v0.16.0 with an update available
  (`uv tool upgrade hermes-agent` as the `hermes` user, then
  `systemctl restart hermes-dashboard hermes-gateway`) — check if this
  still applies.
- **Docker**: not installed as of last check.
- **Model provider**: defaults to Vultr's own paid Inference API — this is
  Vultr's marketplace default, **not** what the user wants, and needs to
  be replaced with Codex/ChatGPT Plus as primary.
- **ChatGPT Plus linking**: was in progress, not confirmed complete. Command:
  `sudo -u hermes /home/hermes/.local/share/uv/tools/hermes-agent/bin/hermes auth add openai-codex --no-browser --manual-paste`
  — this is a device-code flow (prints a URL + short code, user completes
  it in any browser, command polls and completes on its own — no callback
  paste-back actually needed despite the flag name). Note: on a headless
  SSH session, output only appears if you force a pty (`ssh -tt`) — plain
  `ssh user@host 'cmd'` will hang with no output due to Python's output
  buffering when it doesn't detect a terminal.

## What "done" looks like for this session

1. Hermes Agent updated to latest.
2. ChatGPT Plus linked (`hermes auth add openai-codex`), confirmed working.
3. Codex set as the primary/default model provider, replacing Vultr's own
   Inference API default so nothing silently bills against it.
4. One real end-to-end test: send a prompt to Hermes, confirm it actually
   answers using Codex.
5. Optionally, if the user wants to keep going: Docker + Dokploy installed
   (web/container-hosting capability, per the architecture doc) — confirm
   with the user before starting this, don't assume it's in scope for the
   same sitting.

## Ground rules (apply automatically — do not ask permission for these)

- **Memory and git upkeep are your job, not the user's.** Log decisions/
  facts to the catalog as they happen — tagged `hermes`, atomic format
  (one-sentence `body`, structured `attributes`, `relations` edges to
  connect it to related entities, not isolated notes). Commit and push to
  `git@github.com:markstephenguy-bit/hermes.git` as work lands — SSH is
  already configured and working, no auth setup needed.
- **Everything the user says in conversation is priority** — don't
  silently deprioritize what they're asking about.
- **Stay at the altitude the user is at.** This project's history has
  repeated corrections for diving into implementation depth (LM Studio
  config, VPN specifics) before the user asked for that phase — don't
  repeat that pattern. If the immediate task is Codex/VPS setup, talk
  about Codex/VPS setup, not what comes after.
- After every catalog write, also run
  `python3 scripts/export_catalog_memory.py` from the repo root and commit
  the resulting `memory/catalog-export.json` — it's a versioned backup,
  the catalog stays authoritative.

## Where the full history lives

This file is a snapshot, not the source of truth. For anything not covered
above:
- Full decision history, atomically logged with relations:
  `curl "http://192.168.40.250:3003/entities?tags=cs.%7Bhermes%7D"`
- Goals/points tracker (`type=goal` entities, G1–G9, 125 points total,
  25 earned as of 2026-09-24 — G2 and G3 done): 
  `curl "http://192.168.40.250:3003/entities?type=eq.goal&tags=cs.%7Bhermes%7D"`
- Architecture reasoning: [ARCHITECTURE.md](ARCHITECTURE.md)
- Open questions / non-goals: [BACKLOG.md](BACKLOG.md)
- Plain-language vision rollup (may be stale — catalog is truth):
  [VISION.md](VISION.md)
- Repo-specific working conventions: [CLAUDE.md](CLAUDE.md)
