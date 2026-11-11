# Session Seed — Secrets-over-MCP service design (continuing a live discussion)

This replaces the previous seed in full — everything below it was from the
w_workstation Docker env-var pass, now historical (that work is done and
superseded by the architecture simplification below). If you're an agent
picking this up cold, read this whole file before touching anything. If
you're Mark pasting this into a new chat, paste the whole file as your
opening message — the discussion below was mid-thought when the session
ended, not a finished decision.

## What changed tonight (2026-11-02) — full architecture simplification

Mark's direction, stated directly: too many moving parts (NPM + Authentik +
Vaultwarden + per-service SSO), go simple, protect the internet-facing edge
but keep everything inside open. Executed, in order:

1. **Vaultwarden**: exported to a local Bitwarden-format JSON (24 items,
   done by Mark himself via the web UI after I fixed a routing bug blocking
   it — see below), then `docker stop vaultwarden` on `w_workstation`.
   **Stopped, not removed** — data intact if ever needed again.
2. **`lan-local-proxy`** (the old LAN-local mirror of NPM's routing on
   `fileserver`): fully removed — container, its `/home/mark/local-proxy/`
   config+certs directory, and the 5 dead AdGuard rewrite rules it depended
   on. Decided this was pure duplicated complexity, not a capability worth
   keeping: it had already caused two real bugs (stale backend IP, a second
   Authentik wrapper to maintain) for a latency saving nobody could point to
   as mattering. The hosts-file entries on Mark's own laptop that used to
   route through it are also gone (he removed them himself).
3. **Authentik**: `auth_request` wrapper stripped from NPM's
   `hermes.markstephenguy.com` proxy host (now a plain `proxy_pass` to
   `172.18.0.1:9119`), the `hindsight`/`vault`/`netbox`/`auth` NPM proxy
   hosts disabled (renamed `.conf.disabled`, not deleted), then
   `authentik-server`/`authentik-worker`/`authentik-postgresql` **stopped,
   not removed**.
4. **DNS cleanup** (Mark did this himself in Hostinger hPanel): deleted the
   now-dead `netbox`/`vault`/`hindsight`/`auth` A records. Kept `hermes`,
   `www`, `@`.
5. **New: public Hindsight access for remote (non-LAN, non-WireGuard)
   machines.** Found `scripts/hindsight_mcp_http.py` already existed in this
   repo and was already running unused on `w_workstation:8891` (this also
   resolved an old unexplained-process finding from earlier tonight's
   inventory sweep). Exposed it at `hindsight-mcp.markstephenguy.com` via a
   new NPM proxy host (`7.conf`, cert `npm-7`, issued directly via certbot
   since this wasn't created through NPM's own UI/DB) with a bearer-token
   gate (`if ($http_authorization != "Bearer <token>") { return 401; }`) —
   verified working: no/wrong token → `401`, correct token → reaches the
   real backend over the existing WireGuard tunnel. **The token was given to
   Mark directly in chat, not written to any file — if you need it, ask him,
   don't regenerate one blindly.**
6. **Docker cleanup**: freed ~6.5GB total (`w_workstation`: old
   decommissioned Hermes/WordPress/MariaDB images; `fileserver`: an
   already-dead `nginx-proxy-manager` container+image that had been stopped
   10+ days, unrelated to tonight, plus `lan-local-proxy`'s own image).

### Current live routing state

- **Public (only 2 things reachable from the internet)**: `markstephenguy.com`
  /`www` → WordPress on hermes-vps; `hermes.markstephenguy.com` → Hermes's
  own dashboard (its own basic auth, no Authentik); `hindsight-mcp.markstephenguy.com`
  → the Hindsight MCP HTTP sidecar on `w_workstation:8891`, bearer-token gated.
- **LAN/WireGuard-only, no public subdomain, no SSO**: Hindsight (direct
  `192.168.40.100:8888`), NetBox (direct `:8080`) — reached by IP, not name.
- **Unaffected by any of this**: Hermes's own internal calls to Qwen
  (`w_workstation:8090`) and Hindsight (`:8888`) over WireGuard — never went
  through NPM/Authentik/lan-local-proxy. WordPress's AI Engine plugin also
  already reaches Qwen the same way, confirmed working, not something built
  tonight — it just needed verifying.

### Security/resilience findings surfaced tonight, not yet acted on

- **Highest real risk**: `hermes-vps` has `PermitRootLogin yes` +
  `PasswordAuthentication yes` (effective config, confirmed via `sshd -T`).
  Root's password is the same shared password already flagged for rotation
  multiple times in Hindsight and known to have leaked into Hindsight in
  plaintext once already. Root cause of the password-auth setting:
  `/etc/ssh/sshd_config.d/50-cloud-init.conf` sets it back to `yes`,
  overriding `60-cloudimg-settings.conf`'s `no` (sshd uses the first match it
  finds in file-sort order). Not fixed — Mark hasn't given a go-ahead yet.
- **`wp-login.php` has no brute-force protection** — only Akismet/AI
  Engine/Nextend Facebook Connect installed, `fail2ban` only watches `sshd`.
  Not fixed.
- **The new `npm-7` cert (`hindsight-mcp`) has no renewal automation** —
  confirmed *no* cert on this NPM instance has any cron/systemd-timer-based
  renewal at all, not just the new one. Expires 2027-01-31. Not fixed.
- Reassuring finding, confirmed by an actual external nmap scan (not just
  config reading): NPM's admin port 81 and Hermes's old API port 8642 both
  show `filtered` from a genuine outside vantage point, despite a Docker NAT
  rule existing for 81 — the firewall holds in practice, not just in theory.
- `w_workstation` remains the single real point of failure (hosts both Qwen
  and Hindsight; Hermes still has no fallback model, an old open item).
  Qwen's `llama-server.exe` has no restart-on-crash wrapper (pre-existing,
  documented before tonight).

## The live discussion to pick up: a general secrets-over-MCP service

Mark wants to replace Vaultwarden (removed above) with something that works
over MCP and does **not** require an interactive unlock/password step on
every use — the thing that made Vaultwarden painful. He wants one service
Hermes, local AI agents (this laptop), and remote AI agents (other
computers) can all point to, Salt-manageable. The conversation had worked
through:

**What's already settled, as reasoning/explanation, not yet built:**

- MCP is a genuine open standard (JSON-RPC 2.0, `initialize`/`tools/list`/
  `tools/call`), not something custom per client — the same server works
  unmodified for Claude Code, Codex, Antigravity, and Hermes because they all
  implement the same spec. What differs per client is only the *config
  convention* for registering a server (Claude Code's `.mcp.json`, Codex's
  `.codex/config.toml`, Antigravity's `~/.gemini/config/mcp_config.json`,
  Hermes's own `config.yaml` under `mcp_servers:`) — but all of them converge
  on the same two shapes: a local launch command (stdio transport) or a URL
  + headers (HTTP transport).
- The two transports are already proven working examples in this exact repo:
  `scripts/hindsight_mcp.py` (stdio, for LAN-local agents) and
  `scripts/hindsight_mcp_http.py` (HTTP, exposed publicly tonight at
  `hindsight-mcp.markstephenguy.com`). A secrets server would follow the
  identical shape — a thin MCP wrapper in front of wherever the real secret
  values are stored, not a new kind of architecture.
- **Mark's newest framing, not yet explored**: a Docker container, possibly
  at a general `mcp.markstephenguy.com` rather than a secrets-specific name —
  implying he may want *one* MCP gateway that could expose secrets *and*
  other custom capabilities later, not a single-purpose secrets service.
  Worth asking directly whether that's the intent before designing further.
- **The real open tension flagged, not resolved**: any MCP tool that returns
  a raw secret value puts that value into the calling agent's context —
  which is exactly how the Vaultwarden master password already leaked into
  Hindsight once. Recommendation on the table: serve **machine secrets**
  (API keys/tokens — Brave Search, NetBox, the hindsight-mcp token itself)
  freely over MCP, since these are already effectively plaintext in config
  today; do **not** build a tool that serves **human login credentials**
  (VPS root, NPM admin, WordPress admin) — those stay something a human
  reads and types, matching how I've been behaving all session. Mark has not
  yet confirmed or pushed back on this split.

**The four design questions still genuinely open:**

1. Where do the actual secret values live at rest? (plain file vs.
   something encrypted-at-rest — the "no per-use friction" requirement means
   it can't be zero-knowledge/client-side-encrypted the way Vaultwarden was,
   since that model requires a human-supplied key on every unlock by design.)
2. Confirm/revise the machine-secret vs. human-login-secret split above.
3. One service, reached the same proven two-path way Hindsight already is
   (local direct for LAN/WireGuard, public+bearer-token via NPM for
   everything else) — confirm this is the right shape before building.
4. Salt-manageable: realistically a small single-file script (same FastMCP
   style as the Hindsight sidecars) so Salt can start/stop/restart/deploy it
   like everything else this session was driven through.

**RESOLVED 2026-11-10 (research session)**: one gateway, not two. Mark
confirmed `mcp.markstephenguy.com` is a single general-capability MCP
gateway — not a secrets-only service built separately from any Hermes
control surface. This was triggered by a related ask in the same session:
exposing *Hermes itself* as an MCP server so outside harnesses (Claude Code,
Codex, etc.) can call in and control it. Research for that found:

- Hermes's own native `mcp-serve` plugin (`hermes plugins install mcp-serve`)
  is stdio-only and messaging-tools-only (never exposes terminal/file/
  code-exec/process/kanban/delegation) — not a fit for a network-reachable
  Docker gateway.
- A community proposal to expose Hermes's full tool registry via FastMCP
  (NousResearch/hermes-agent issue #342) was closed by the maintainer as
  incomplete/underspecified — treat "wrap everything" as a known hard
  problem, not a quick build.
- The viable path: Hermes already runs a complete, documented REST/
  OpenAI-compatible API server (port 9119, `API_SERVER_KEY` bearer auth —
  `/v1/chat/completions`, `/v1/runs` family, `/api/sessions` family,
  `/api/jobs`, `/v1/skills`, `/v1/toolsets`, `/v1/capabilities`). A thin MCP
  wrapper translating MCP tool calls into calls against *that* REST API —
  same shape as `scripts/hindsight_mcp.py`/`hindsight_mcp_http.py` — is the
  sound architecture, not the native plugin.

**Implication for this gateway's scope**: `mcp.markstephenguy.com` should end
up exposing both tool families — secrets tools (per the design below) *and*
Hermes-control tools (`hermes_chat`, `hermes_run_*`, `hermes_session_*`,
`hermes_job_*`, plus `hermes_capabilities`/`hermes_skills_list`/
`hermes_toolsets_list` as MCP resources) — as one Docker-packaged MCP server,
not two.

**Expanded again 2026-11-10**: Mark also wants this gateway to **replace the
current `infra` MCP server** (`scripts/infra_mcp.py`, registered today as a
local stdio server in `.mcp.json` via `scripts/infra_mcp_run.sh`). Its real
tools are `salt_run` (Salt `cmd.run`/any function, with the Windows-vs-POSIX
shell auto-detection logic worth preserving) and `salt_minion_status`
(ping-all). It also has a third tool, `netbox_quick_scan`, which calls
`netbox_sync.py` — **do not carry this one forward**: NetBox itself is
decommissioned (2026-11-06, see memory), so this tool is already dead code
pointed at nothing, independent of this consolidation.

So the gateway is now four tool-families: secrets, Hermes-control, vector-RAG
(from the same session, see memory `project_hermes_vector_rag_research`), and
infra/Salt control. One real design flag worth surfacing before building: Salt
gives effectively root-level control over every host on the network, and this
gateway's other half (secrets, and possibly a public bearer-token HTTP path
like `hindsight-mcp.markstephenguy.com`'s) implies at least some internet
exposure — Salt control sitting behind the same bearer-token gate as Hindsight
recall is a much bigger blast radius if that token ever leaks. Worth an
explicit look at transport/auth-per-tool-family (e.g. Salt only over the
stdio/LAN path, never the public HTTP path) rather than one flat auth model
for everything, when this gets built.

**Next step**: the four secrets-design questions below are still open and
unresolved. Resolve those, confirm the combined tool surface above, then
build — closely mirroring the already-working Hindsight sidecar pattern.

## Standing rules, unchanged

Memory upkeep and git upkeep are still Claude's job per `CLAUDE.md` — commit
and push as work lands, retain decisions to Hindsight (bank `hermes`) as
they happen. Vaultwarden is retired as the secrets source; its replacement
is the open discussion above, not yet live. Don't re-add Authentik or
`lan-local-proxy` without a real reason — both were deliberately removed
tonight, not lost by accident.
