# Backlog / Open Questions

## The fork that needs deciding first

Hermes is independent of LocalForge (decided 2026-09-22 — see catalog entity
`hermes-independent-of-localforge-2026-09-22`), so this is now a pure code-
reuse question, not a scope-boundary one:

- **(a) Share code with LocalForge** — reuse its existing LM Studio
  connection code / HTTP contract (`delegate_task` plumbing, `finish_reason`
  handling, etc.) as a starting point.
- **(b) Build Hermes's own client from scratch** — accept some duplication,
  keep LocalForge completely untouched.

Nothing else below should really be worked until this is picked, since it
determines where the code lives and what gets reused.

## Resolved

- **Remote access mechanism (2026-09-22):** password-gated web UI behind
  existing DuckDNS + Nginx Proxy Manager, path-based location. No VPN/tunnel
  client on the connecting device — see ARCHITECTURE.md for the reasoning
  (Georgia Pacific laptop constraint) and catalog entity
  `hermes-remote-access-decision-2026-09-22`.

## Other open decisions

- **Model choice** — keep `gemma-4-12b-it` (already loaded, already proven
  for LocalForge's use) vs. a model chosen specifically for chat-agent /
  tool-calling use. Needs an actual tool-calling capability check, not a
  guess.
- **Cloud fallback provider** — whether a single-account router (e.g.
  OpenRouter) is worth the complexity vs. calling one cloud API directly
  when local capability isn't enough.
- **Gateway software** — hand-rolled routing vs. LiteLLM or similar vs. no
  separate gateway at all (Hermes agent code picks local-vs-cloud itself).
- **UI implementation** — the *access path* is decided (above); the UI
  itself (existing self-hostable chat-UI project vs. custom-built) is not.
- **Auth mechanism at the NPM Custom Location** — plain HTTP Basic Auth
  (simple, works immediately) vs. an app-level login page (nicer, more
  work).
- **Agent-controlled web hosting** — per ARCHITECTURE.md's "network
  resources are agent capabilities" principle: what does it mean for Hermes
  to host a page *it* built — same container as the chat UI, or a separate
  capability it can invoke?

## Non-goals (for now)

- Re-documenting the home network in this repo — that's the catalog's job.
- Standing up a second reverse proxy / DNS / tunnel stack — NPM + DuckDNS
  already does this job (decided above).
- Committing to specific software (LiteLLM, a specific model, a specific
  tunnel provider) before the LocalForge-vs-separate fork above is resolved.
