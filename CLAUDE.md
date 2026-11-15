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

Secrets (API keys, tokens, credentials) live in secure local environment files
(mode 0600, e.g. `~/.config/.../credentials.env` or local profile `.env`) —
**never hardcoded in code or committed to this repo**. Vaultwarden and the
old catalog secrets table are both retired/tombstoned; do not query or reference
Vaultwarden for secrets.

## Logging progress — this project's actual memory

Hermes-specific memory (decisions, live inventory snapshots, progress) lives
in **Cognee Cloud** (hosted at `api.aws.cognee.ai`, replaced Hindsight and Graphiti
on 2026-11-15) — not the old fileserver catalog, not Hindsight on w_workstation
(turned off), and not new markdown files in this repo or prose dumped into a chat
session. Cognee Cloud is reached through the `cognee` MCP server
(`scripts/cognee_cloud_mcp.py`, registered in this repo's `.codex/config.toml`,
`~/.codex/config.toml`, `~/.claude.json`, `.mcp.json`, and in Antigravity's
`~/.gemini/config/mcp_config.json`, talking HTTPS to Cognee Cloud using static API
keys from `~/.config/cognee-cloud/credentials.env`). This survives across every
future session/tool (Claude Code, Codex, Antigravity, Hermes) without re-explaining itself.

- `remember(data, dataset_name, background)` — write a new fact/decision/progress
  note into Cognee Cloud (defaults to dataset `hindsight_migration` or `main_dataset`).
- `recall(query, datasets, search_type, top_k)` — semantic / hybrid graph search
  over stored knowledge.
- `list_datasets()` — inspect datasets in the workspace.

Keep this repo's own docs (README/ARCHITECTURE/BACKLOG) as a *current-state
summary* a human can read at a glance — update them in place, don't let them
drift from Cognee Cloud, but don't treat them as the memory store either.

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
  conversation gets written to Cognee Cloud (dataset `hindsight_migration`
  or `main_dataset`, via the `cognee` MCP server) as it happens. The user
  should never have to say "remember this."
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
