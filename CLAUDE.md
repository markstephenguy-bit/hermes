# Hermes — working notes for Claude Code

This repo is the source for Hermes, a self-hosted personal AI agent for the
home network. See [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md),
and [BACKLOG.md](BACKLOG.md) first.

## Before assuming anything about the network

Real hosts, services, and credentials live in the catalog — Postgres +
PostgREST on `server` (192.168.40.250:3003), documented in
`Home Claude/CLAUDE.md` on the shared drive (`//server.local/share/Projects/Home Claude`).
Query it rather than trusting anything cached in this repo's docs, e.g.:

```bash
curl "http://192.168.40.250:3003/hosts"
curl "http://192.168.40.250:3003/services"
curl "http://192.168.40.250:3003/entities?search=fts.hermes"
```

Secrets (API keys, tokens) go in the catalog's `secrets` table
(`pgp_sym_encrypt`-backed), never hardcoded here or committed to this repo.
See the shared `CLAUDE.md` for the exact `secret_set`/`secret_get` calls.

## Logging progress — this project's actual memory

Hermes-specific memory (decisions, live inventory snapshots, progress) lives
in the catalog as `entities` tagged `hermes`, not as new markdown files in
this repo or as prose dumped into a chat session. This is deliberate: an
edge-based store you query on demand costs far less session context than a
growing pile of markdown, and it survives across every future session/tool
(Claude Code, Antigravity) without re-explaining itself.

- Query everything tagged for this project:
  `curl "http://192.168.40.250:3003/entities?tags=cs.%7Bhermes%7D"`
- Add new context the same way any home-lab entity gets added (see shared
  `CLAUDE.md`'s "How to log new context"), always including `"tags": ["hermes", ...]`.
- Link related entities via the `relations` table (subject/predicate/object)
  as they come up — e.g. `hermes` entities relating to `host` w_workstation,
  or to `entity` LocalForge decisions — so `graph_recall` gets more useful
  as the project grows instead of staying a pile of disconnected rows.
- Use `search_similar` (semantic) when you don't have an exact keyword, `fts`
  tag search when you do.

Keep this repo's own docs (README/ARCHITECTURE/BACKLOG) as a *current-state
summary* a human can read at a glance — update them in place, don't let them
drift from the catalog, but don't treat them as the memory store either.

### Backup: catalog memory is a single point of failure

The catalog only exists on `server` (Postgres) — nothing else backs it up.
`scripts/export_catalog_memory.py` dumps all `hermes`-tagged entities and
their relations to `memory/catalog-export.json`, which gets committed and
pushed like any other change. Run it (`python3 scripts/export_catalog_memory.py`)
and commit the result whenever new `hermes`-tagged entities/relations are
added to the catalog — treat it as part of the same "log this to the
catalog" step, not a separate chore. This file is a dead backup only, never
read *from* it while the catalog is reachable.

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
  conversation gets written to the catalog (tagged `hermes`) as it happens,
  including `relations` edges linking it to what it's related to — not just
  isolated entities. The user should never have to say "remember this."
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
