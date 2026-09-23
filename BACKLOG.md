# Backlog / Open Questions

## The fork that needs deciding first

- **(a) Extend LocalForge** — grow its existing bridge to also serve Hermes,
  reusing the same LM Studio connection and whatever code already works
  (`delegate_task` plumbing, `finish_reason` handling, etc.), accepting that
  LocalForge's "stay minimal, single-purpose" charter has to bend.
- **(b) Stand up Hermes separately** — a new process alongside LocalForge,
  accepting duplicated LM Studio client code but keeping LocalForge
  untouched and single-purpose.

Nothing else below should really be worked until this is picked, since it
determines where the code lives and what gets reused.

## Other open decisions

- **Remote access mechanism** — Tailscale (container already exists on
  `server`, currently logged out) vs. MeshCentral (deployed, no agents yet)
  vs. Cloudflare Tunnel (nothing set up) vs. something else. Prefer reusing
  what's already half-present over adding a new mechanism.
- **Model choice** — keep `gemma-4-12b-it` (already loaded, already proven
  for LocalForge's use) vs. a model chosen specifically for chat-agent /
  tool-calling use. Needs an actual tool-calling capability check, not a
  guess.
- **Cloud fallback provider** — whether a single-account router (e.g.
  OpenRouter) is worth the complexity vs. calling one cloud API directly
  when local capability isn't enough.
- **Gateway software** — hand-rolled routing vs. LiteLLM or similar vs. no
  separate gateway at all (Hermes agent code picks local-vs-cloud itself).
- **UI** — what "chat app you can reach from your phone" actually is:
  existing self-hostable web UI vs. custom-built.

## Non-goals (for now)

- Re-documenting the home network in this repo — that's the catalog's job.
- Standing up a second reverse proxy / DNS / tunnel stack when an existing
  one (NPM, AdGuard, the dormant Tailscale/MeshCentral) might already cover
  it.
- Committing to specific software (LiteLLM, a specific model, a specific
  tunnel provider) before the LocalForge-vs-separate fork above is resolved.
