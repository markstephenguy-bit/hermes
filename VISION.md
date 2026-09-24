# Vision

A readable snapshot of the vision conversation so far — synthesized from the
catalog (`entities` tagged `hermes`), which remains the authoritative,
queryable source. This file can drift out of date; when it does, trust the
catalog (`memory/catalog-export.json` in this repo is the versioned backup
of it) over this narrative.

## What Hermes is for

Replace paid ChatGPT Plus and Claude Pro with a self-hosted personal agent
built on hardware already owned, keeping Google One as the one subscription
that stays. A single paid LLM gateway supplements frontier-model access
instead of two separate chat subscriptions.

## Hermes is the master harness

The user talks to **Hermes**, not to Claude Code directly. Claude Code is
understood as a bootstrap tool — it's doing this setup work by hand only
because Hermes doesn't exist yet to do it itself. Long-term, agentic/coding
work (the kind Claude Code does today) becomes something Hermes *delegates
to*, not something the user opens separately.

This lines up with what Nous Research's actual **Hermes Agent** product
already does: sub-agent delegation with its own terminals/scripts, 5
sandboxed execution backends (local/Docker/SSH/Singularity/Modal), a Tool
Gateway (web search, image gen, TTS, browser automation) and model access
via **Nous Portal**, all under one subscription. Hermes Desktop is the
official native GUI (Mac/Windows/Linux), architected as a thin client that
talks over WebSocket/REST to a `hermes serve` backend running wherever you
put it — which is exactly the shape this project needs.

## Interface strategy

Leaning toward **Signal/Telegram as the primary interface** — messaging
traffic is unremarkable on any network, no proxy or special setup needed,
which matters given the Georgia Pacific constraint below. A password-gated
web UI (`theguylab.duckdns.org/hermes`, via the existing DuckDNS + Nginx
Proxy Manager setup) stays as a landing page for remote access, and Hermes
Desktop gets used natively when practical (e.g. at home). Not fully locked —
a leaning, not a final decision.

## The Georgia Pacific constraint

The user's employer is actively averse to unusual network activity on
company-managed devices. This shaped the remote-access decision directly:
no VPN/tunnel client anywhere (Tailscale, MeshCentral, and Cloudflare Tunnel
were all explicitly rejected for requiring a client on the connecting
device). A password wall behind a normal HTTPS domain, or a message to a
normal messaging app, both look like ordinary traffic.

**Tension flagged, not resolved:** two later asks point the opposite
direction — a home-based proxy specifically to route the GP workstation's
traffic around its Zscaler security proxy, and using the GP workstation
itself as a candidate host for the Hermes backend. Both are logged as open
items tagged `risk`, since they're a meaningfully bigger corporate-policy
exposure than the "just browse a website" design the rest of the access
strategy was built around.

## Model & routing strategy

- **The model is Hermes** (Nous Research's model line) — not an open
  evaluation. Specific version/size not pinned down yet.
- **Routing criterion is free-vs-paid, not abstract complexity.** LM Studio
  (local, free) is always tried first. It should also perform the
  escalation decision itself — a RouteLLM-style self-assessment of whether
  it can handle a prompt or needs to hand off — so even that judgment call
  costs nothing.
- **Paid gateway** only gets reached when the local model can't handle it,
  and picks the frontier model at that point. Nous Portal may already *be*
  this gateway (it aggregates model access + a Tool Gateway under one
  subscription) — open question is whether it also does complexity-based
  auto-routing, or only unified access/billing.
- LM Studio should run **multiple local models concurrently**, not one
  fixed chat model.

## Network resources as agent capabilities

Core design principle: home network resources (compute, storage, the
ability to host a web page, etc.) are meant to become capabilities Hermes
itself can use and eventually control — implementation-agnostic. This is
expected to be **emergent**, not a punch list to build proactively: specific
appliance/resource integrations happen naturally as Hermes reaches for them
post-spinup, not as pre-built scaffolding.

## Where Hermes lives (so it doesn't sleep)

Recommendation (not yet confirmed): run `hermes serve` on **`server`** —
already always-on 24/7, already hosts the persistent home-lab services
(Nginx Proxy Manager, AdGuard, the catalog, Portainer), no dependency on any
user session, 152GB free disk. `w_workstation` stays the free GPU/LM Studio
resource `hermes serve` calls out to over LAN — its own sleep/power settings
are a separate, smaller open question. The GP workstation is **not**
recommended as the backend host: its power management is IT-managed and
outside the user's control, on top of the corporate-policy risk already
flagged above.

## What's still genuinely open

- Which specific Hermes model version/size, sized to fit `w_workstation`'s
  RTX A4000 (16GB VRAM).
- Whether Nous Portal covers the "free-first, escalate on need" routing
  decision itself, or something else needs to sit in front of it.
- The Zscaler-bypass-proxy and GP-workstation-as-backend-host questions —
  flagged as risk, not resolved.
- Auth mechanism for the web UI landing page (Basic Auth vs. an app login).
- Whether to share code with `LocalForge` or build Hermes's own LM Studio
  client from scratch.

See [BACKLOG.md](BACKLOG.md) for the full list with more detail, and the
catalog (`?tags=cs.%7Bhermes%7D`) for the complete, linked record.
