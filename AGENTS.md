# Hermes — working notes for Codex, Antigravity, and other agentic tools

This repo is the source for Hermes, a self-hosted personal AI agent for the
home network. See [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md),
and [BACKLOG.md](BACKLOG.md) first.

## Read NEXT_SESSION.md before anything else

[NEXT_SESSION.md](NEXT_SESSION.md) is the single most current, authoritative
record of infrastructure state — more current than ARCHITECTURE.md/BACKLOG.md,
which lag behind it and get reconciled only periodically. If anything in those
two files conflicts with NEXT_SESSION.md, **NEXT_SESSION.md wins.** It's
written as a session-opening brief; read it as a status doc regardless of
which tool you are.

If the catalog or Hindsight (below) is unreachable — no LAN/WireGuard access,
e.g. working from outside the home network without the laptop's WireGuard
tunnel up — this repo's own NEXT_SESSION.md is the only record of project
state (`memory/catalog-export.json` is a dead backup of the retired catalog,
not current — see the Hindsight backup note below). Treat NEXT_SESSION.md as
load-bearing in that case, not a backup.

## Before assuming anything about the network

Real hosts, services, and credentials live in the catalog — Postgres +
PostgREST on `fileserver` (192.168.40.2:3003, migrated off `server` on
2026-09-30 after repeated unclean crashes there), documented in
`Home Codex/AGENTS.md` on the shared drive (`//server.local/share/Projects/Home Codex`).
Query it rather than trusting anything cached in this repo's docs, e.g.:

```bash
curl "http://192.168.40.2:3003/hosts"
curl "http://192.168.40.2:3003/services"
curl "http://192.168.40.2:3003/entities?search=fts.hermes"
```

Secrets (API keys, tokens, passwords) live in **Vaultwarden on the VPS only**
(`https://theguylab.duckdns.org/vault/`, via the `bw` CLI or the `bitwarden`
MCP connector) — never hardcoded here or committed to this repo. The
fileserver catalog's old `secrets` table is retired as of 2026-10-14; all 16
entries were migrated to Vaultwarden and it must not be used or queried for
secrets going forward, even as a fallback. One secrets source, full stop.

## Logging progress — this project's actual memory

Hermes-specific memory (decisions, live inventory snapshots, progress) lives
in **Hindsight**, the memory system running on a w_workstation Docker
deployment (192.168.40.100:8888) — not the old fileserver catalog and not
new markdown files in this repo or prose dumped into a chat session.
Hindsight is reached through the `hindsight` MCP server
(`scripts/hindsight_mcp.py`, registered in this repo's `.codex/config.toml`
and in Antigravity's `~/.gemini/config/mcp_config.json`, talking plain HTTP
to Hindsight directly — no SSH hop needed) rather than a raw `curl` to the
fileserver Postgres endpoint. This survives across every future session/tool
(Codex, Antigravity, Claude Code) without re-explaining itself.

- `retain(content, context, document_id, metadata)` — write a new fact/
  decision/progress note. One sentence or two in `content`, specifics
  (numbers, paths, config) in `metadata` as string values, not prose.
- `recall(query, tags, budget)` — semantic search over stored memory.
- `reflect(query)` — ask a question and get a synthesized answer instead of
  raw matches.
- `list_memories` / `get_entities` / `list_banks` — inspect what's stored.

Migrated 2026-10-15: the fileserver Postgres/PostgREST catalog (previously
`entities` tagged `hermes`) is retired as Hermes's memory store — do not
read or write `hermes`-tagged entities there going forward. `hosts`/
`services` tables on that catalog are a separate, non-Hermes concern and
are out of scope for this migration (don't touch them as part of Hermes
work without asking first).

Keep this repo's own docs (README/ARCHITECTURE/BACKLOG) as a *current-state
summary* a human can read at a glance — update them in place, don't let them
drift from Hindsight, but don't treat them as the memory store either.

### Backup: Hindsight is a single point of failure

Hindsight's data only exists on its w_workstation Docker deployment —
nothing else backs it up yet. The old `scripts/export_catalog_memory.py` /
`memory/catalog-export.json` pair backed up the retired fileserver catalog
and is now historical only (dead backup of a dead store — do not treat it
as current). An equivalent periodic export of the Hindsight `hermes` bank
(it has its own `GET .../banks/{bank_id}/export` endpoint) has not been
built yet — this is a known gap, not a solved one.

## Standing rules inherited from the home lab

- Don't stand up infrastructure that duplicates something that already
  exists (reverse proxy, DNS, remote access) — check the catalog's
  `services` table first.
- Minimize speculative scaffolding — see BACKLOG.md's non-goals.

## Ground rules for this project specifically (set 2026-09-22)

These override the usual "ask before doing X" defaults for the actions
listed below, *for this project*:

- **Memory upkeep is Codex's (and Antigravity's) job, not the user's.**
  Never wait to be told to save something. Every decision, correction, or
  fact that comes up in conversation gets written to Hindsight (bank
  `hermes`, via the `hindsight` MCP server) as it happens. The user should
  never have to say "remember this."
- **Git upkeep is Codex's job, not the user's.** Commit as work lands and
  push too, no need to ask first. SSH access was set up 2026-09-23 (key
  registered with GitHub, remote `git@github.com:markstephenguy-bit/hermes.git`)
  — push works. If a push ever fails, verify with `ssh -T git@github.com`
  before assuming credentials broke.
- **Everything the user says in conversation is a priority signal, full
  stop.** Don't silently deprioritize something the user spent time
  explaining in favor of what Codex judges more architecturally important.
  Capture it, act on it, log it.
- **Codex is a bootstrap tool.** Hermes doesn't exist yet, which is
  the only reason Codex is doing this work by hand. The expectation is
  that this whole maintenance role (memory, repo upkeep, network changes)
  eventually moves *into* Hermes itself once it exists. Build with that
  handoff in mind — e.g. prefer capabilities/APIs a future agent could call
  over one-off manual steps only Codex can do.
