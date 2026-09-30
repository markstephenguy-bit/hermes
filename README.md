# Hermes

A self-hosted personal AI agent + inference gateway for the home network — the
long-term goal is to replace paid ChatGPT Plus / Claude Pro subscriptions with
something built on hardware already in the house, with a single paid cloud
account (for frontier-model fallback) instead of two. See
[VISION.md](VISION.md) for the current state of that vision in plain
language, [ARCHITECTURE.md](ARCHITECTURE.md) for technical detail, and
[BACKLOG.md](BACKLOG.md) for what's still undecided.

## Relationship to LocalForge

Hermes is a standalone project — a personal agent + chat UI meant to be used
directly (browser, phone), not a tool inside a Claude Code session. It is
**not** bound by the scope limits of `LocalForge` (`Home Claude/LocalForge`
on the shared drive), a separate, narrower project that bridges Claude Code
to the same LM Studio instance. That project's "stay minimal, single-purpose"
charter was written for its own use case and does not constrain Hermes.

Where it's useful, Hermes should reuse what LocalForge already proved out —
same underlying hardware (LM Studio on `w_workstation`), same HTTP contract,
maybe the same connection code — but as prior art to borrow from, not a
boundary to respect. See [ARCHITECTURE.md](ARCHITECTURE.md) for the current
thinking on how much to share vs. build separately.

## Status

As clarified by the user on 2026-09-30, Hermes uses local AI with Codex as
its second model for more complex prompts. Claude Code currently handles
setup while local AI and home network configuration are still in progress.
The user intends to move that setup role to Codex and retire Claude Code
later; no immediate removal is planned. This setup role is separate from
Codex's model role inside Hermes.

## Source of truth

This repo describes Hermes-specific design and code. It does **not**
re-document the home network — real hosts, services, and credentials live in
the catalog (Postgres + PostgREST at `192.168.40.2:3003`). See
`CLAUDE.md` in this repo for how a Claude Code session working here should
query that catalog before assuming anything about the network.
