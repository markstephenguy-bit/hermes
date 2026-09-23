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

## Standing rules inherited from the home lab

- Don't stand up infrastructure that duplicates something that already
  exists (reverse proxy, DNS, remote access) — check the catalog's
  `services` table first.
- Minimize speculative scaffolding — see BACKLOG.md's non-goals. Resolve the
  LocalForge-vs-separate fork before writing code, not after.
