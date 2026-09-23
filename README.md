# Hermes

A self-hosted personal AI agent + inference gateway for the home network — the
long-term goal is to replace paid ChatGPT Plus / Claude Pro subscriptions with
something built on hardware already in the house, with a single paid cloud
account (for frontier-model fallback) instead of two.

## Relationship to LocalForge

There is a separate, narrower project already running: `LocalForge`
(`Home Claude/LocalForge` on the shared drive), which bridges **Claude Code**
to LM Studio on `w_workstation` as a single-purpose MCP tool
(`delegate_task`, `embed_text`, `check_local_llm_status`). That project's
explicit non-goal is "building a general-purpose multi-agent framework."

Hermes *is* that general-purpose thing — a standalone agent + chat UI meant to
be used directly (browser, phone), not as a tool inside a Claude Code session.
Where both projects want the same underlying resource (LM Studio on
`w_workstation`), Hermes should reuse it rather than standing up a second
inference server that fights the first for VRAM. See
[ARCHITECTURE.md](ARCHITECTURE.md) for how that boundary is meant to work.

## Status

Scaffolding only — no code yet. See [ARCHITECTURE.md](ARCHITECTURE.md) for
current design thinking and [BACKLOG.md](BACKLOG.md) for the open decisions
that need to be made before writing code, starting with the biggest one:
whether Hermes extends LocalForge's existing bridge or stands up separately
alongside it.

## Source of truth

This repo describes Hermes-specific design and code. It does **not**
re-document the home network — real hosts, services, and credentials live in
the catalog (Postgres + PostgREST at `192.168.40.250:3003`). See
`CLAUDE.md` in this repo for how a Claude Code session working here should
query that catalog before assuming anything about the network.
