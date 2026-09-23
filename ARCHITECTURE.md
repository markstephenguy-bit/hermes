# Architecture

Working assumptions as of project start (2026-09-22). Verify against the
catalog before trusting any of this in a future session — hardware/software
state on `w_workstation` changes as LocalForge work continues.

## Core design principle: network resources are agent capabilities

Hermes isn't just "a chat UI backed by a local model." The home network's
existing resources (compute, storage, the ability to host a web page, etc.)
are meant to become capabilities *the agent itself* can use and eventually
control — implementation-agnostic. E.g. "the agent can host a web page it
built" matters; *which* web server software does it, or which host it runs
on, doesn't. Keep this in mind when deciding where new pieces live: prefer
designs where a capability is something Hermes can invoke/control, not just
something Claude Code wired up once by hand.

## What's real right now

- **`w_workstation`** (192.168.40.100, Windows 11) has the actual GPU: an
  NVIDIA RTX A4000, 16GB VRAM. LM Studio is already running there with
  `gemma-4-12b-it@q8_0` loaded (~12GB) plus `nomic-embed-text-v1.5` for
  embeddings — roughly 4GB of headroom left before a second model could be
  loaded alongside it.
- **`server`** (192.168.40.250, Ubuntu 24.04) is the existing Docker host —
  already runs Nginx Proxy Manager, AdGuard (LAN DNS), Portainer, the
  catalog (`catalog-db`/`catalog-api`), and other public/internal services.
  Any new Hermes container work should join this host's existing patterns
  (see the catalog `services` table) rather than reinventing reverse-proxy
  or DNS handling.
- **Remote access — decided (2026-09-22):** password-gated web UI behind the
  existing DuckDNS domain (`theguylab.duckdns.org`) and Nginx Proxy Manager,
  as a new path-based Custom Location (matching the existing `/wp`, `/beszel`
  pattern) — e.g. `theguylab.duckdns.org/hermes`. Deliberately **not**
  Tailscale (dormant container on `server`) or MeshCentral (no agents
  installed) or Cloudflare Tunnel — all three require installing a client on
  whatever device is connecting, which is the opposite of the actual
  requirement: this needs to work unmodified on a company-managed laptop
  (Georgia Pacific) where installing VPN/tunnel clients would itself look
  like the "strange goings-on" the user is explicitly trying to avoid. A
  password wall behind a normal HTTPS domain requires installing nothing —
  it's indistinguishable from browsing any other site. Same URL, same login,
  from this laptop at home, this laptop at work, or this laptop at a hotel.
  See catalog entity `hermes-remote-access-decision-2026-09-22`.
- `LocalForge`'s bridge already proves out the core idea (Claude Code / an
  agent process talking to LM Studio's OpenAI-compatible API over LAN) —
  the code at `Home Claude/LocalForge/bridge/server.py` is a working
  reference for the HTTP contract, timeouts, and `finish_reason == "length"`
  gotchas already discovered there.

## Open architectural question: one bridge or two?

LocalForge's bridge talks to LM Studio for Claude Code's benefit. Hermes
needs something that talks to LM Studio for a human's benefit (chat UI,
possibly tool-calling agent loops). Two credible shapes:

1. **Extend LocalForge's bridge** to also serve a Hermes-facing API, so
   there's one process owning the LM Studio connection.
2. **Separate Hermes gateway process**, accepting that both talk to LM
   Studio's `:1234` independently (LM Studio can serve multiple concurrent
   clients; the actual constraint is VRAM/one-model-at-a-time, not
   connection count).

Not decided yet — see [BACKLOG.md](BACKLOG.md).

## Routing tiers (concept, not yet built)

The rough shape carried over from initial brainstorming — tiers, not a
committed design:

1. **Local (free):** LM Studio on `w_workstation` for the bulk of requests.
2. **Cloud fallback (paid, one account):** a single OpenRouter-style account
   for requests that exceed local capability or when the workstation is
   offline — model and routing mechanism (hand-rolled vs. LiteLLM or
   similar) not yet chosen.

No gateway software (LiteLLM or otherwise) is installed anywhere yet — this
is a design sketch, not a deployed component.
