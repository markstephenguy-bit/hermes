# MCPHub-based Gateway (hwdsl2/docker-mcp-gateway, aka "UplinkCrate") vs. MCPJungle

Scope note: "MCPHub-based gateway" refers to two related but distinct repos:
- **samanhappy/mcphub** — the upstream engine itself (Node.js/TypeScript + React, Apache-2.0).
- **hwdsl2/docker-mcp-gateway**, now renamed **hwdsl2/uplinkcrate** — a thin Docker-Compose-style wrapper that bundles `samanhappy/mcphub` behind a Caddy reverse proxy that enforces Bearer-token auth. This is the "one container fronting multiple MCP capabilities" packaging the user named.
MCPJungle's canonical repo is confirmed as **github.com/mcpjungle/MCPJungle** (Go, MPL-2.0), docs at docs.mcpjungle.com.

## SINGULAR: is it genuinely one container/endpoint, or multiple pieces?

### Takeaway
hwdsl2/UplinkCrate is the closest to a true single-container deployment (one Docker image bundling Caddy + MCPHub, file-based storage by default). MCPHub itself can also run as one container with no external DB (file-based `mcp_settings.json`) unless you opt into its Database Mode or Smart Routing features. MCPJungle, despite marketing itself as "one place to manage... MCP servers," ships a `docker-compose.yaml` that defines **two** containers (a Postgres 17 `db` service plus the `mcpjungle` server) — Postgres is a hard dependency in its own quickstart, not optional.

### Cited Findings
- hwdsl2/uplinkcrate's own description: "Self-hosted multi-server MCP (Model Context Protocol) gateway with Bearer token auth, powered by MCPHub and Caddy... through one endpoint." Single container stack: base image `samanhappy/mcphub`, Caddy as always-on auth proxy, internal port 3001 (MCPHub) exposed via port 3000, persistent data at `/var/lib/mcp`. — [GitHub repo](https://github.com/hwdsl2/docker-mcp-gateway)
- samanhappy/mcphub: "Single Container: Docker image (`samanhappy/mcphub`) with bundled frontend... Database Support: Optional PostgreSQL for production via Database Mode... Headless Mode: Supports `DISABLE_WEB=true` for API-only deployments." Default storage is file-based, not a mandatory external DB. — [GitHub repo](https://github.com/samanhappy/mcphub)
- MCPHub's optional "Smart Routing" (semantic tool search) does require additional database/vector-search configuration, but this is an opt-in feature layered on top of the base gateway, not required for basic multi-server proxying. — [docs.mcphubx.com/features/smart-routing](https://docs.mcphubx.com/features/smart-routing) (third-party-hosted docs mirror found via search; not the primary samanhappy repo, flagged as secondary)
- MCPJungle's quickstart instructs: `curl -O .../docker-compose.yaml && docker compose up -d`. The fetched docker-compose.yaml defines two services: `db` (Postgres 17, with health checks, port 5432) and `mcpjungle` (built from `ghcr.io/mcpjungle/mcpjungle`, port 8080, depends on `db` being healthy). — [raw docker-compose.yaml](https://raw.githubusercontent.com/mcpjungle/MCPJungle/main/docker-compose.yaml)
- MCPJungle also ships a CLI tool and a separate dashboard UI as part of its normal usage pattern, per its own README description ("Server, CLI tool, dashboard UI"). — [GitHub repo](https://github.com/mcpjungle/MCPJungle)
- MCPJungle does also advertise a "single binary" option per its repo description, but the documented/recommended quickstart path is the two-container Compose setup with Postgres, not the bare binary. — [GitHub repo](https://github.com/mcpjungle/MCPJungle) (binary-only deployment details not found in primary docs; gap noted below)

### Inferences
- For a home-lab user wanting the minimum moving parts, hwdsl2/UplinkCrate's packaging is the most "singular" of the three options examined — it's explicitly designed as a one-container wrapper around MCPHub specifically to avoid the user having to stand up Caddy and MCPHub separately.
- MCPJungle's reliance on Postgres as the default/documented deployment path is a meaningful strike against "one container" simplicity, even though a standalone-binary mode may technically exist.

### Gaps
- Whether MCPJungle's standalone binary mode can run with SQLite or an embedded DB instead of Postgres (avoiding the second container) was not confirmed in primary docs — the commit log mentions a "SQLite database path configuration" commit (May 20, 2026 per MCPJungle's own commit history), suggesting SQLite support may exist as an alternative, but this wasn't verified against current docs.

## POWERFUL: auth, access control, logging, hot-reload

### Takeaway
MCPHub (and by extension UplinkCrate, which just fronts it with Caddy) has the richer feature set: OAuth 2.0 (both client- and server-side), JWT+bcrypt accounts, social login, per-user credential binding, tool/prompt/resource visibility controls, activity logging, and documented hot-reload of upstream servers via its dashboard. UplinkCrate itself only adds a simpler Bearer-token layer via Caddy on top of that. MCPJungle currently supports only Bearer-token auth (OAuth is explicitly "coming soon," not yet shipped) but does have tool-group-based per-client filtering and access-control/observability hooks for shared deployments.

### Cited Findings
- MCPHub auth: "Bearer tokens (optional, disabled by default for MCP endpoints)... OAuth 2.0 (both client and server modes)... JWT + bcrypt for local accounts... Social login via Better Auth (GitHub, Google)." Access control: "Per-user credentials binding with encrypted storage... Server and group visibility controls... Tool, Prompt, and Resource exposure management... Authentication required by default on MCP endpoints." — [GitHub repo](https://github.com/samanhappy/mcphub)
- MCPHub hot-reload: "Explicitly supports 'hot-swappable config' enabling server addition/removal/updates without downtime." — [GitHub repo](https://github.com/samanhappy/mcphub)
- MCPHub logging/observability: "Tool-call activity inspection... Request status and latency tracking... Server logs aggregation... Health checks and connection monitoring." — [GitHub repo](https://github.com/samanhappy/mcphub)
- MCPHub OAuth for upstream servers: supports an `oauth.identityMode: "personal"` setting so each dashboard user authorizes independently, with user-associated Bearer keys honoring their own OAuth binding, including on `/mcp/<group>` aggregate routes. — [GitHub PR #1318](https://github.com/samanhappy/mcphub/pull/1318), [PR #1364](https://github.com/samanhappy/mcphub/pull/1364)
- UplinkCrate (hwdsl2) auth: "Primary Auth: Bearer token (auto-generated on first start)... Key Storage: Persisted in `/var/lib/mcp/.api_key`... Caddy Role: Always active, enforces Bearer token auth" with optional `MCP_API_KEY` override. — [GitHub repo](https://github.com/hwdsl2/docker-mcp-gateway)
- UplinkCrate hot-reload: "MCPHub dashboard at `http://<server>:3000/` allows adding/removing servers 'without restarting the container.' Changes persist to volume." — [GitHub repo](https://github.com/hwdsl2/docker-mcp-gateway); README itself did not contain a dedicated architecture section or benchmark/changelog content when fetched directly. — [raw README.md](https://raw.githubusercontent.com/hwdsl2/docker-mcp-gateway/main/README.md)
- MCPJungle auth: "MCPJungle does not support OAuth flow for authentication yet. However, support for OAuth flow is coming soon." Current mechanism is Bearer-token-based: `mcpjungle register --name huggingface ... --bearer-token <token>` attaches `Authorization: Bearer <token>` to requests made *to* that upstream server, and MCPJungle separately issues per-client access tokens for talking *to* the gateway (`Authorization: Bearer {token}` on gateway-facing requests). — [WebSearch result citing MCPJungle docs, exact page not individually fetched]
- MCPJungle registration schema (from mintlify-hosted docs) supports fields `name`, `transport` (`streamable_http`/`sse`/`stdio`), `description`, `url`, `bearer_token`, `oauth_redirect_uri`, `oauth_client_id`, `oauth_client_secret`, `oauth_scopes`, `session_mode`, and arbitrary `headers` — meaning OAuth *client* fields exist for upstream registration even though the search result above says OAuth as a full gateway-auth flow is not yet shipped; these two claims likely describe different things (OAuth-to-upstream config fields existing vs. a mature/complete OAuth flow) and are not fully reconciled by primary sources. — [docs.mcpjungle.com guide](https://mcpjungle.mintlify.app/guides/register-http-servers)
- MCPJungle access control/observability: "optional tool groups to expose only the tools a client should see," and "access-control and observability hooks" for shared deployments, plus "per-client tokens" so "each client can reach" specific servers in an enterprise mode. — [docs.mcpjungle.com](https://docs.mcpjungle.com/) and [GitHub repo](https://github.com/mcpjungle/MCPJungle)
- MCPHub also has a guarded Authorization-header-passthrough mechanism for upstream servers, added as an explicit admin opt-in (`systemConfig.routing.allowAuthorizationPassthrough`, default off) after a credential-isolation fix blocked it outright — relevant for ChatGPT-style connectors that rely on header passthrough. — [GitHub PR #1453](https://github.com/samanhappy/mcphub/pull/1453)

### Inferences
- MCPHub is architecturally the more "powerful" gateway of the two on this criterion: it has a materially broader auth matrix (OAuth2 + bearer + JWT accounts + social login) and more mature observability/hot-reload documentation than MCPJungle, which is still pre-OAuth on its own admission.
- For a home-lab setup with custom self-written HTTP MCP servers, MCPJungle's explicit `bearer_token`/`headers` fields per upstream registration are simple and sufficient; MCPHub's passthrough opt-in is more powerful but has more moving parts (admin opt-in flag, credential-isolation caveats) to get right.

### Gaps
- Exact current-state documentation of MCPJungle's OAuth roadmap (what "coming soon" means in terms of timeline) was not found in a dated primary source — the "coming soon" framing came from a secondary aggregator search result, not a directly fetched/quoted doc page, and should be treated as provisional.
- Did not verify whether MCPJungle's Bearer-token gateway auth can be scoped per-tool (vs. only per-server/tool-group) — only tool-group-level filtering was confirmed in primary sources.

## LONG-LASTING: maintainer, activity, stars, releases, abandonment signals

### Takeaway
samanhappy/mcphub is the largest and most actively developed of the three repos by a wide margin (2.6k stars, very high recent commit velocity) but is a solo-maintainer ("samanhappy") project with no visible organizational backing found. MCPJungle is backed by its own GitHub org (mcpjungle), has 1.5k stars, a long steady release history (10+ tagged releases from March 2026 through October 30, 2026) and commits into November 3, 2026 — the strongest "org, not just solo dev" signal among the three. hwdsl2/UplinkCrate is a small, very new, single-maintainer side project (5 stars, 2 forks, 1 open issue, first commit July 4 2026, one tagged release v2026.10.1 on Oct 24 2026) that is actively committed-to as of Nov 2 2026 but has essentially no community traction yet and carries real "future abandonment" risk typical of a brand-new one-person wrapper repo.

### Cited Findings
- samanhappy/mcphub: 2.6k stars, 362 forks, only 7 open issues, Apache-2.0, 1,003 total commits, with 20+ commits across just Oct 29–Nov 3 2026 (e.g., 5 commits on Nov 3, 3 on Nov 2, 4 on Nov 1, 4 on Oct 31, 8 on Oct 30, 5 on Oct 29). — [GitHub repo](https://github.com/samanhappy/mcphub), [commits/main](https://github.com/samanhappy/mcphub/commits/main)
- samanhappy/mcphub latest-release version/date was not surfaced by the repo-page fetch ("Latest Release: Not specified in provided content") — a gap, not a confirmed absence of releases.
- mcpjungle/MCPJungle: ~1.5k stars (per repo-page fetch; WebSearch separately reported "1,254 stars and 158 forks" — these two figures disagree, likely because the WebSearch snippet is from an aggregator/cached page rather than the live repo page; treat the live fetch's 1.5k/196 as more current), MPL-2.0, 79 open issues, 280 total commits. — [GitHub repo](https://github.com/mcpjungle/MCPJungle); conflicting secondary figure — [WebSearch aggregator snippet, source page unclear]
- MCPJungle releases (newest→oldest): 0.4.7 (Oct 30, 2026) — "addressed vulnerable Go modules and security improvements" — 0.4.6 (Aug 2, 2026), 0.4.5 (May 20, 2026), 0.4.4 (May 14, 2026), 0.4.3 (May 7, 2026), 0.4.2 (May 4, 2026), 0.4.1 (Apr 20, 2026), 0.4.0 (Apr 17, 2026), 0.3.7 (Apr 8, 2026), 0.3.6 (Mar 13, 2026). — [GitHub releases](https://github.com/mcpjungle/MCPJungle/releases)
- MCPJungle recent commits: Nov 3, 2026 ("Remove legacy docs from readme"), Oct 30, 2026 ("update docs & AGENTS.md"), Oct 26, 2026 ("AGENTS.md"), two commits Oct 25, 2026 (mcp-go upgrade, Go module security updates), then a gap back to Aug 2, 2026 (host binding config), May 2026 (SQLite path config, dashboard UI), April 2026 (architecture diagram, docs site). — [commits/main](https://github.com/mcpjungle/MCPJungle/commits/main)
- hwdsl2/uplinkcrate (formerly docker-mcp-gateway): 5 stars, 2 forks, 1 open issue, MIT license, 77 commits total. — [GitHub repo](https://github.com/hwdsl2/docker-mcp-gateway)
- hwdsl2/uplinkcrate commit timeline: earliest visible commit July 4, 2026; recent commits Nov 2, Oct 29, three on Oct 24, Oct 21, Oct 18, Oct 17, two on Oct 11 2026 (including an Oct 11 "Rebrand as UplinkCrate" commit). — [commits/main](https://github.com/hwdsl2/docker-mcp-gateway/commits/main)
- hwdsl2/uplinkcrate has exactly one tag: v2026.10.1, released Oct 24, 2026, described as "Initial source release." — [tags page](https://github.com/hwdsl2/uplinkcrate/tags) (note: tags URL resolved under the renamed `uplinkcrate` slug)

### Inferences
- On raw longevity signals (stars, org backing, steady multi-season release cadence), MCPJungle > MCPHub > UplinkCrate, even though MCPHub wins on sheer commit velocity/community size.
- MCPHub's much larger open-issue backlog relative to MCPJungle's (7 vs. 79) is ambiguous on its own — it could mean MCPHub triages/closes issues faster, or that MCPJungle accumulates issues because it's younger/smaller; raw issue count isn't a reliable abandonment signal by itself and wasn't cross-checked against closed-issue counts for either project (see Gaps).
- UplinkCrate is best read as "actively maintained by one person right now" rather than "long-lasting" — it has no release history to speak of beyond a single Oct 2026 tag, and as a thin wrapper it is also exposed to upstream risk if samanhappy/mcphub changes its image/config format.

### Gaps
- Closed-issue counts (vs. open) were not obtained for any of the three repos — only open-issue counts were confirmed, so true issue-resolution velocity (a better abandonment signal than raw open count) is unverified.
- No named company/organization backing was found for samanhappy/mcphub beyond the individual GitHub handle "samanhappy" — could not confirm solo-dev vs. org status definitively either way from primary sources fetched.
- MCPHub's own tagged-release history/changelog page was not fetched directly (only the repo landing page), so its release cadence could not be directly compared to MCPJungle's documented release list above.

## FAST: deterministic proxy architecture, no LLM step, benchmarks

### Takeaway
Both MCPHub and MCPJungle are architecturally plain HTTP relays/routers for their core proxying paths — no LLM reasoning step sits in the default request path for either. MCPHub does have one *optional*, separately-enabled feature ("Smart Routing," at `/mcp/$smart`) that performs vector-embedding semantic search over tool descriptions to pick relevant tools; this is not a full LLM completion/reasoning call, but it is a non-trivial additional computation step beyond pure deterministic routing, and is opt-in rather than default. Neither project publishes any formal latency/throughput benchmark numbers in the primary sources checked.

### Cited Findings
- MCPHub default routing is via static routes: `/mcp`, `/mcp/{group}`, `/mcp/{server}`, plus the optional `/mcp/$smart` and `/mcp/$smart/{group}` for Smart Routing. — [GitHub repo](https://github.com/samanhappy/mcphub)
- MCPHub Smart Routing "uses vector semantic search to automatically find the most relevant tools for any given task... requires additional setup compared to basic MCPHub usage, including database configuration and environment variables for search parameters." This confirms it is a separate, opt-in subsystem layered on top of the base deterministic proxy, using vector/embedding similarity rather than an LLM completion call in the request path. — [docs.mcphubx.com/features/smart-routing](https://docs.mcphubx.com/features/smart-routing) (third-party docs mirror, secondary source)
- No latency, throughput, or benchmark figures were found in samanhappy/mcphub's repo page or README content fetched. — [GitHub repo](https://github.com/samanhappy/mcphub)
- UplinkCrate/docker-mcp-gateway README explicitly contains no performance metrics, rate-limit specs, or latency benchmarks ("Not included" on direct fetch of the raw README). — [raw README.md](https://raw.githubusercontent.com/hwdsl2/docker-mcp-gateway/main/README.md)
- MCPJungle's documented architecture (CLI registers servers by name+URL+transport, gateway exposes a single streamable-HTTP MCP endpoint at `/mcp`) is a straightforward reverse-proxy/router pattern with no mention of an LLM-in-the-loop routing step anywhere in the fetched README or docs pages. — [README.md](https://raw.githubusercontent.com/mcpjungle/MCPJungle/main/README.md), [docs.mcpjungle.com](https://docs.mcpjungle.com/)
- No latency/benchmark numbers were found for MCPJungle in any primary source fetched.

### Inferences
- For the user's "FAST" requirement (deterministic proxy, no LLM reasoning in the path), both projects satisfy it in their *default* configuration. MCPHub's Smart Routing is the only feature across either project that introduces non-deterministic, content-based tool selection, and it must be deliberately enabled — leaving it off keeps MCPHub/UplinkCrate just as "pure proxy" as MCPJungle.
- The complete absence of published benchmarks for both projects means any FAST claim rests on architectural inference (plain HTTP relay, no LLM call) rather than measured numbers — this should be stated as unverified-by-measurement in the final report.

### Gaps
- Neither project publishes quantitative latency/throughput benchmarks in any primary source found (GitHub repo pages, READMEs, docs sites) — this is a documented absence, not an oversight in research.
- Did not independently verify MCPHub's Smart Routing implementation details (e.g., is the embedding model local or does it call an external/cloud embedding API, which would add network latency and an external dependency) — the docs mirror fetched describes "vector semantic search" but not the embedding backend.

## CROSS-CLIENT: Claude Code, Antigravity/Gemini, ChatGPT remote connector, custom self-hosted MCP server registration

### Takeaway
Neither project's primary documentation, as fetched, shows an explicit Antigravity or Gemini client config example, and neither explicitly documents confirmed interoperability with ChatGPT's remote MCP connector feature in its own primary docs (this had to be pieced together from GitHub PRs/search, not a docs page stating "works with ChatGPT"). Both projects do document exact config syntax for registering a custom self-hosted MCP server over streamable-HTTP (and MCPJungle explicitly supports SSE and stdio too); MCPHub additionally has shipped a guarded Authorization-header-passthrough feature specifically relevant to connector-style clients like ChatGPT, while MCPJungle's bearer-token-per-upstream-server model is simpler but has no OAuth-based gateway auth yet, which would need checking against ChatGPT connector's actual requirements.

### Cited Findings
- **Claude Code / `.mcp.json`-style config**: Neither hwdsl2/UplinkCrate's README nor MCPJungle's README contained a Claude-Code-specific `.mcp.json` example when fetched directly — both instead show "Claude Desktop" JSON config (same underlying `mcpServers` schema Claude Code also uses, but not explicitly labeled for Claude Code). UplinkCrate's Claude Desktop example: `{"mcpServers": {"gateway": {"url": "http://localhost:3000/mcp", "transport": "streamable-http", "headers": {"Authorization": "Bearer <api_key>"}}}}`. — [raw README.md](https://raw.githubusercontent.com/hwdsl2/docker-mcp-gateway/main/README.md). MCPJungle's Claude Desktop example instead routes through the `mcp-remote` npm shim: `{"mcpServers": {"mcpjungle": {"command": "npx", "args": ["mcp-remote", "http://localhost:8080/mcp", "--allow-http"]}}}`. — [raw README.md](https://raw.githubusercontent.com/mcpjungle/MCPJungle/main/README.md)
- **Antigravity/Gemini**: No example found in any primary source fetched for either project. Confirmed gap for both.
- **ChatGPT remote connector**: Not addressed in either project's own README/docs as fetched. For MCPHub, the closest primary evidence is engineering-level: a merged PR restoring an admin-opt-in `systemConfig.routing.allowAuthorizationPassthrough` so an upstream server can receive the client's `Authorization` header unmodified ("shared by HTTP MCP and OpenAPI paths... Administrators can use Settings → Keys to save a separate MCPHub auth header and enable the switch") — this is the kind of header-passthrough behavior ChatGPT-style connectors often need, but the PR describes it as a security-guarded opt-in, not an endorsed/documented "ChatGPT works" integration. — [GitHub PR #1453](https://github.com/samanhappy/mcphub/pull/1453). A separate secondary WebSearch summary claimed MCPHub supports a ChatGPT-connector OAuth setup flow ("Set Authentication to OAuth... Under Client registration, choose User-Defined OAuth Client... Copy the ChatGPT Redirect URI... Paste the Client ID and Client Secret") but this could not be traced to a specific fetched primary-source page/URL during this research pass, so it is flagged as **unverified** rather than asserted as confirmed fact.
- For MCPJungle, no ChatGPT-specific documentation or confirmation was found in any primary source; combined with MCPJungle's own admission that OAuth support is "coming soon," and ChatGPT's remote connector feature generally requiring either OAuth or a specific header-based auth scheme, MCPJungle's current Bearer-token-only gateway auth is **not confirmed** to be compatible with ChatGPT's connector requirements — this is a gap, not a verified failure.
- **Custom self-hosted MCP server registration syntax**:
  - MCPJungle (confirmed via its own docs guide): CLI — `mcpjungle register --name context7 --url https://mcp.context7.com/mcp` (works for any reachable streamable-HTTP URL, not just bundled servers); full JSON schema —
    ```json
    {
      "name": "deepwiki",
      "transport": "streamable_http",
      "description": "Deepwiki MCP Server",
      "url": "https://mcp.deepwiki.com/mcp",
      "bearer_token": "<optional bearer token>",
      "oauth_redirect_uri": "http://127.0.0.1:38291/oauth/callback",
      "oauth_client_id": "<optional pre-registered client id>",
      "oauth_client_secret": "<optional pre-registered client secret>",
      "oauth_scopes": ["mcp.read"],
      "session_mode": "stateless",
      "headers": {"<custom-header>": "<value>"}
    }
    ```
    Transport field accepts `"streamable_http"`, `"sse"`, or `"stdio"` — so SSE upstream servers at an arbitrary host:port are explicitly supported, though the detailed SSE-specific field layout wasn't shown in the fetched guide. — [docs.mcpjungle.com guide](https://mcpjungle.mintlify.app/guides/register-http-servers)
  - MCPHub: base config file `mcp_settings.json` registers servers as JSON entries under `mcpServers`; a stdio example confirmed directly from the repo (`{"mcpServers": {"time": {"command": "npx", "args": ["-y", "time-mcp"]}}}`). For streamable-HTTP custom servers, the general MCP-ecosystem convention MCPHub follows (per secondary-source confirmation, not a directly-fetched MCPHub doc page) is `{"mcpServers": {"<name>": {"type": "streamable-http", "url": "http://<host>:<port>"}}}` — this exact syntax was **not independently confirmed against MCPHub's own docs site** in this research pass and should be treated as moderately-confident, not fully primary-sourced. — [GitHub repo](https://github.com/samanhappy/mcphub) (stdio example); streamable-http syntax via [WebSearch secondary summary, specific MCPHub doc URL not captured]
  - UplinkCrate just inherits whatever MCPHub's `mcp_settings.json`/dashboard supports (it doesn't add its own registration mechanism beyond the `MCP_SERVERS` env var for its small built-in catalog on first run) — so custom arbitrary-host:port servers would be added the same way as in plain MCPHub (via the dashboard or `mcp_settings.json`), not via a distinct UplinkCrate-specific syntax. This inheritance is inferred from the README's framing of UplinkCrate as "MCPHub ... + Caddy" rather than independently confirmed with a worked custom-server example in UplinkCrate's own README. — [raw README.md](https://raw.githubusercontent.com/hwdsl2/docker-mcp-gateway/main/README.md)

### Inferences
- MCPJungle currently has the more precisely-documented (in its own primary docs) registration schema for an arbitrary custom HTTP/SSE MCP server, including explicit optional OAuth-client and custom-header fields — useful for Mark's "custom self-written HTTP-transport MCP servers" requirement.
- Neither gateway can be asserted, from primary sources alone, to be "confirmed working behind ChatGPT's remote MCP connector" — this would need to be tested directly rather than taken from docs, since neither project's own documentation makes that specific claim.
- If Claude Code, Antigravity, and a generic Python agent all just need "URL + headers," both gateways satisfy that baseline (both expose a single streamable-HTTP MCP endpoint reachable with a bearer header) — the harder unresolved question is specifically ChatGPT's connector, which is the one client in Mark's list with the most specific (OAuth-oriented) auth expectations.

### Gaps
- No primary-source Antigravity/Gemini-specific config example exists for either project — this is a real documentation gap in both projects, not a research miss.
- The ChatGPT-connector-compatibility claim for MCPHub (OAuth-based connector setup walkthrough) surfaced only via a WebSearch synthesis and could not be re-traced to a specific fetched doc URL in this pass — flag as needing direct verification (e.g., by testing against a live MCPHub instance) before treating it as fact.
- MCPHub's exact `mcp_settings.json` field syntax for a streamable-HTTP/SSE custom upstream was not confirmed by directly fetching MCPHub's own docs site (only its GitHub repo landing page and a secondary aggregator were checked) — worth a follow-up fetch of MCPHub's dedicated docs site (not just the repo README) if precision on this exact syntax matters before adoption.
- Did not test either gateway live against an actual ChatGPT remote-connector registration flow — all findings here are documentation/code-level, not empirically verified end-to-end.
