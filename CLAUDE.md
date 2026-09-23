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

## Logging progress

Log real decisions and events (architecture choices made, hardware/software
state discovered, problems hit and solved) to the catalog as `entities`
(`type=log-entry` / `type=decision`), the same convention used for the rest
of the home lab — not as new markdown files in this repo. Keep this repo's
own docs (README/ARCHITECTURE/BACKLOG) as the current-state summary, and
update them in place rather than letting them drift from the catalog.

## Standing rules inherited from the home lab

- Don't stand up infrastructure that duplicates something that already
  exists (reverse proxy, DNS, remote access) — check the catalog's
  `services` table first.
- Minimize speculative scaffolding — see BACKLOG.md's non-goals. Resolve the
  LocalForge-vs-separate fork before writing code, not after.
