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

Every harness (Claude Code, Codex, Antigravity, Hermes) reaches Salt
(`infra`), Cognee Cloud, Hermes's own REST API, and the native
`hermes mcp-serve` plugin (messaging/conversation tools, web search/extract,
vision, image-gen, skills, TTS) through a **single MCP registration**,
`mcp_proxy`, instead of one registration per server per harness.

As of 2026-11-20, this is a single Docker container, **`mcpserver`**
(image `mcpserver:local`, built out-of-band from
`/home/mark/services/mcpserver/` on `fileserver`, not from this repo),
listening on `fileserver` (192.168.40.2) port **8800**:
`http://192.168.40.2:8800/mcp` (LAN) / `http://10.60.0.2:8800/mcp` (from
`hermes-vps`, over the existing WireGuard tunnel), `Authorization: Bearer`
auth using the same `MCP_PROXY_GATEWAY_TOKEN` value as before. It composes
Cognee Cloud, `infra_mcp` (Salt), and `hermes_mcp` tools, plus a
`hermes_serve` namespace proxying the native stdio `hermes mcp-serve
--tools` plugin on `hermes-vps` (over a dedicated SSH key/config bind-mounted
into the container). Reads the same `/home/mark/.config/mcp-proxy/credentials.env`
on fileserver for its secrets.

This replaces the earlier two-hop architecture (MCPHub/UplinkCrate Docker
gateway on port 3100, fronting a separate systemd-`--user` sidecar
`scripts/mcp_proxy_sidecar.py` on loopback `172.17.0.1:8700`) — both pieces
were cut over to `mcpserver` on 2026-11-17 (commit `ca4b06d`) and fully
removed (container + image + systemd unit) on 2026-11-20 after verifying
every harness worked through the new container alone. `scripts/mcp_proxy_sidecar.py`
in this repo is no longer what's running in production; treat it as
historical reference unless `mcpserver`'s own source (on fileserver,
outside this repo) is what you actually need to change.

Registered as `mcp_proxy` in: `.mcp.json` / `~/.claude.json` (Claude Code),
`.codex/config.toml` / `~/.codex/config.toml` (Codex — bearer token read
from the `MCP_PROXY_GATEWAY_TOKEN` env var via
`~/.config/environment.d/mcp-proxy.conf` + `~/.bashrc`), `~/.gemini/config/mcp_config.json`
(Antigravity), and `~/.hermes/config.yaml` on `hermes-vps`. No harness has
any other MCP server registered for home-lab capabilities — `mcp_proxy` is
the only one, everywhere, including on Hermes itself.

New capability, including for other harnesses to call (Salt, Hermes-REST,
any future custom tool): add it to `mcpserver`'s own source on fileserver,
not to a fourth per-harness config file.

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
  over stored knowledge. **Always pass `datasets=["main_dataset"]` explicitly**
  unless `hindsight_migration` is the deliberate target — leaving `datasets`
  unscoped lets Cognee's auto-routing rank a near-empty `hindsight_migration`
  result above the real answer in `main_dataset`, with no error to flag it
  (confirmed live 2026-11-21, same failure mode on `search()` too).
- `list_datasets()` — inspect datasets in the workspace.
- `ingestion_status(dataset_id)` — check a background `remember` call until processing completes or errors.

Added 2026-11-21, same `cognee_cloud_mcp.py` wrapper, lower-level than the four
above (`remember` = `add_data`+`cognify`+improve in one call; `recall` = a
session-aware, auto-routed `search`):

- `add_data(raw_data, dataset_name, labels, run_in_background)` — ingest without
  building the graph yet.
- `cognify(datasets, run_in_background, custom_prompt, chunk_size)` — build the
  graph from data already added via `add_data()`.
- `search(query, search_type, datasets, top_k, only_context)` — one explicit
  `SearchType` (see Cognee's enum — `GRAPH_COMPLETION`, `CYPHER`, `CODE`, `TEMPORAL`,
  etc.), no session semantics.
- `forget(dataset, data_id, everything, memory_only, clean_history)` —
  **destructive, cannot be undone.** Confirm with the user before calling with
  `everything=True` or without `data_id`.
- `list_dataset_data(dataset_id)` — list the data items inside one dataset
  (paginated).
- `quotas_usage()` — storage used vs. the workspace quota.

Full endpoint reference: [docs.cognee.ai/cognee-cloud/http-api](https://docs.cognee.ai/cognee-cloud/http-api).
Skills/agents/auth/integrations endpoints exist on the same API but aren't
wrapped here — different auth model, out of scope for this memory gateway.

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
