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

## One gateway for every harness — `mcp_proxy`

As of 2026-11-15, every harness (Claude Code, Codex, Antigravity, Hermes)
reaches Salt (`infra`), Cognee Cloud, and Hermes's own REST API through a
**single MCP registration**, `mcp_proxy`, instead of one registration per
server per harness. Two pieces, both on `fileserver` (192.168.40.2):

1. **MCPHub/UplinkCrate** (Docker, port 3100) — the public-facing gateway
   every harness registers: `http://192.168.40.2:3100/mcp` (LAN) /
   `http://10.60.0.2:3100/mcp` (from `hermes-vps`, over the existing
   WireGuard tunnel), `Authorization: Bearer` auth. Bearer token and the
   auto-generated admin password live in
   `/home/mark/.config/mcp-proxy/credentials.env` on fileserver.
2. **The sidecar** (`scripts/mcp_proxy_sidecar.py`, systemd `--user` service
   on fileserver, loopback-only on `127.0.0.1`/`172.17.0.1:8700`) — composes
   the existing `cognee_cloud_mcp.py`, `infra_mcp.py`, and `hermes_mcp.py`
   servers into one FastMCP process via `mount()`. This is MCPHub's one
   registered upstream today; it's also where any future bespoke internal
   tool should get added, since MCPHub itself only proxies, it doesn't host
   custom logic.

Registered as `mcp_proxy` in: `.mcp.json` / `~/.claude.json` (Claude Code),
`.codex/config.toml` / `~/.codex/config.toml` (Codex — bearer token read
from the `MCP_PROXY_GATEWAY_TOKEN` env var via
`~/.config/environment.d/mcp-proxy.conf` + `~/.bashrc`), `~/.gemini/config/mcp_config.json`
(Antigravity), and `~/.hermes/config.yaml` on `hermes-vps`. `hermes-mcp-serve`
(stdio-only, SSH-spawned, messaging tools) is **not** folded in yet — stays
registered separately.

New capability, including for other harnesses to call (Salt, Hermes-REST,
any future custom tool): add it to the sidecar, not to a fourth per-harness
config file.

## Logging progress — this project's actual memory

Hermes-specific memory (decisions, live inventory snapshots, progress) lives
in **Cognee Cloud** (hosted at `api.aws.cognee.ai`, replaced Hindsight and Graphiti
on 2026-11-15) — not the old fileserver catalog, not Hindsight on w_workstation
(turned off), and not new markdown files in this repo or prose dumped into a chat
session. Cognee Cloud is reached through the `mcp_proxy` gateway above (its
sidecar mounts `scripts/cognee_cloud_mcp.py`, which talks HTTPS to Cognee
Cloud using static API keys from `~/.config/cognee-cloud/credentials.env`).
This survives across every future session/tool (Claude Code, Codex,
Antigravity, Hermes) without re-explaining itself.

- `remember(data, dataset_name, background)` — write a new fact/decision/progress
  note into Cognee Cloud (defaults to the shared `main_dataset`; use `hindsight_migration` explicitly to search or append historical migration material).
- `recall(query, datasets, search_type, top_k)` — semantic / hybrid graph search
  over stored knowledge.
- `list_datasets()` — inspect datasets in the workspace.
- `ingestion_status(dataset_id)` — check a background `remember` call until processing completes or errors.

The `hindsight_migration` dataset contains historical statements that may describe retired services as active. Use current configuration and `main_dataset` for current-state answers.

Migrated 2026-11-15: Hindsight's entire memory store (3,347 facts, 272 batches)
was migrated into Cognee Cloud dataset `hindsight_migration`. Hindsight has been
completely decommissioned and permanently removed: all containers, images, volumes,
plugins, scripts, and configurations have been purged from `w_workstation`,
`hermes-vps`, and this repository. Hermes relies on built-in memory + Cognee Cloud MCP tools.

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
  conversation gets written to Cognee Cloud's `main_dataset` (not
  `hindsight_migration` — that's historical-only, see above) via the
  `cognee` MCP server's `remember()` tool. The user should never have to
  say "remember this."
  - **Write as each finding lands, not in one batch at the end.** Concretely:
    call `remember()` right after (a) confirming a root cause, (b) applying
    or verifying a fix, (c) discovering something that contradicts existing
    memory, (d) closing out a discrete sub-task — don't wait to accumulate
    several of these into one end-of-session write.
  - **Never say "I saved this" / "I've logged that" without actually having
    called `remember()` first.** This happened for real in this project
    (2026-11-15): a finding was narrated as saved and wasn't, which could
    have silently lost it. If in doubt, make the call before claiming it.
  - After a long or multi-part task, do a quick `recall()` sanity check that
    the key findings actually landed — don't just trust that prior
    `remember()` calls succeeded.
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
