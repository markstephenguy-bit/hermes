# Hermes — working notes for Claude Code

This repo is the source for Hermes, a self-hosted personal AI agent for the
home network. See [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md),
and [BACKLOG.md](BACKLOG.md) first.

## Before assuming anything about the network

Real hosts, services, and credentials live in the catalog — Postgres +
PostgREST on `fileserver` (192.168.40.2:3003, migrated off `server` on
2026-09-30 after repeated unclean crashes there), documented in
`Home Claude/CLAUDE.md` on the shared drive (`//server.local/share/Projects/Home Claude`).
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

**Onboarding a new AI system onto Vaultwarden** (a new laptop, a Claude Code
install at the law office, etc.): run `scripts/onboard_bitwarden_mcp.sh` on
that machine. It logs into Vaultwarden, unlocks the vault (master password
typed locally on that machine, never passed through an agent), saves a CLI
session token under `~/.claude/mcp_servers/bitwarden/`, and registers the
`bitwarden` MCP server for that machine's local AI tools. After that one
run, that machine's agents can call Vaultwarden live via MCP with no further
password entry, until the saved session goes stale — re-run the script to
refresh it. Scripts that need a secret outside of MCP (e.g.
`scripts/salt_client.py`) read the same saved session and shell out to
`bw get ...` directly, so there's no per-call password handling either.

## Logging progress — this project's actual memory

Hermes-specific memory (decisions, live inventory snapshots, progress) lives
in **Hindsight**, the memory system already running on `hermes-vps` (bank
`hermes`), not the old fileserver catalog and not new markdown files in this
repo or prose dumped into a chat session. Hindsight binds to `127.0.0.1:9177`
on the VPS only, so it's reached through the `hindsight` MCP server
(`scripts/hindsight_mcp.py`, deployed to `hermes@10.60.0.1:~/.hermes/mcp_servers/hindsight/`
and invoked over SSH as the `hermes` user — registered in this repo's
`.mcp.json` and `.codex/config.toml`, and in Antigravity's
`~/.gemini/config/mcp_config.json`) rather than a raw `curl` to a Postgres
endpoint. This survives across every future session/tool (Claude Code,
Codex, Antigravity) without re-explaining itself.

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

Hindsight's data only exists on `hermes-vps` — nothing else backs it up yet.
The old `scripts/export_catalog_memory.py` / `memory/catalog-export.json`
pair backed up the retired fileserver catalog and is now historical only
(dead backup of a dead store — do not treat it as current). An equivalent
periodic export of the Hindsight `hermes` bank (it has its own
`GET .../banks/{bank_id}/export` endpoint) has not been built yet — this is
a known gap, not a solved one.

## Standing rules inherited from the home lab

- Don't stand up infrastructure that duplicates something that already
  exists (reverse proxy, DNS, remote access) — check the catalog's
  `services` table first.
- Minimize speculative scaffolding — see BACKLOG.md's non-goals.

## Ground rules for this project specifically (set 2026-09-22)

These override the usual "ask before doing X" defaults for the actions
listed below, *for this project*:

- **Memory upkeep is Claude's job, not the user's.** Never wait to be told
  to save something. Every decision, correction, or fact that comes up in
  conversation gets written to Hindsight (bank `hermes`, via the `hindsight`
  MCP server) as it happens. The user should never have to say "remember
  this."
- **Git upkeep is Claude's job, not the user's.** Commit as work lands and
  push too, no need to ask first. SSH access was set up 2026-09-23 (key
  registered with GitHub, remote `git@github.com:markstephenguy-bit/hermes.git`)
  — push works. If a push ever fails, verify with `ssh -T git@github.com`
  before assuming credentials broke.
- **Everything the user says in conversation is a priority signal, full
  stop.** Don't silently deprioritize something the user spent time
  explaining in favor of what Claude judges more architecturally important.
  Capture it, act on it, log it.
- **Claude Code is a bootstrap tool.** Hermes doesn't exist yet, which is
  the only reason Claude Code is doing this work by hand. The expectation is
  that this whole maintenance role (memory, repo upkeep, network changes)
  eventually moves *into* Hermes itself once it exists. Build with that
  handoff in mind — e.g. prefer capabilities/APIs a future agent could call
  over one-off manual steps only Claude Code can do.
