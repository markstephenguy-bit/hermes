# McpManager (daniel3303) vs. mcp-gateway (mspstack) — Self-Hosted MCP Gateway Comparison

## SINGULAR — is it genuinely one container/endpoint?

### Takeaway
McpManager is the stronger "singular" option: one Docker container, SQLite baked into a volume, no other required services. mcp-gateway is also a single required container (Node + SQLite, no native deps), but its own repo ships a docker-compose stack that includes an OpenBao container by default — OpenBao is explicitly documented as optional/skippable, so it does not disqualify the "singular" claim but it is a mark against it out of the box.

### Cited Findings
- McpManager quick-start is a single `docker run` command: `docker run -p 5057:8080 -v mcpmanager-data:/app/data daniel3303/mcpmanager:latest`, with SQLite persisted in the same container's `/app/data` volume — no second service required — [GitHub README](https://github.com/daniel3303/McpManager).
- McpManager repo root has no docker-compose file; only a single `Dockerfile` at repo root — [GitHub contents](https://github.com/daniel3303/McpManager).
- mcp-gateway's own compose file (`docker/docker-compose.yml`) defines three services: `gateway` (built from local Dockerfile, port 3100, required), `openbao` (image `quay.io/openbao/openbao:latest`, explicitly dev-mode/in-memory, documented as "for evaluation only"), and a commented-out example upstream (`mcp-itglue`) — [docker-compose.yml](https://raw.githubusercontent.com/mspstack/mcp-gateway/main/docker/docker-compose.yml).
- mcp-gateway's own docs state a secret store is "optional" and a complete deployment path exists that skips OpenBao entirely, using `${VAR}` env-var interpolation for upstream credentials instead; tradeoff is that credential rotation then requires a container restart instead of a live 5-minute refresh — [docs/standalone-secrets.md](https://raw.githubusercontent.com/mspstack/mcp-gateway/main/docs/standalone-secrets.md).
- mcp-gateway package has no native dependencies and requires Node ≥24, SQLite for storage — [GitHub README summary via WebFetch](https://github.com/mspstack/mcp-gateway).

### Inferences
- For a home-lab deployment that only needs plain bearer-token/env-var auth to custom upstreams (Mark's stated use case), mcp-gateway can in fact run as a single container if OpenBao is omitted from the compose file — the "multi-container" framing in the default repo compose file is a documentation/default-config choice, not an architectural requirement.
- McpManager is simpler to stand up as strictly one container because its repo doesn't even offer a multi-service compose option to begin with.

### Gaps
- Neither project's docs give a published resource-footprint (RAM/CPU) comparison for the single-container deployment.

## POWERFUL — auth, RBAC, logging, hot-reload

### Takeaway
mcp-gateway has materially richer access-control and auth depth (OAuth 2.1 resource server + DCR facade, role-based tool tiers, per-tool allow/deny, network ACLs, per-user credentials) and confirmed hot-reload of upstream tool lists without restart. McpManager has solid basics (bearer/API-key/basic/env-var auth, claims-based authorization, per-tool enable/disable, detailed per-call request logging with a live log viewer) but no documented hot-reload claim and coarser (claims/namespace-based, not role-tiered) access control.

### Cited Findings
- McpManager auth: ASP.NET Identity multi-user accounts, Bearer-token "scoped API keys" prefixed `mcpm_`, claims-based authorization, per-namespace API-key scoping; upstream transports support Bearer, API key, Basic auth, or env vars — [README via WebFetch](https://github.com/daniel3303/McpManager).
- McpManager logging: "Every tool execution tracked with parameters, response, success status, and execution time," plus a real-time streaming log viewer filterable by server/level/time-range, backed by Serilog (console + rolling file) — [README via WebFetch](https://github.com/daniel3303/McpManager).
- McpManager access control granularity is per-namespace/per-API-key and per-tool enable/disable; no explicit role hierarchy (viewer/editor/admin) is documented — [README via WebFetch](https://github.com/daniel3303/McpManager).
- No explicit hot-reload claim found for McpManager; its only two docs files are an architecture diagram and a screenshots folder, nothing describing live server add/remove behavior — [docs contents](https://api.github.com/repos/daniel3303/McpManager/contents/docs). A targeted web search for "hot reload"/"without restart" turned up nothing specific to this project — treated as an explicit gap, not confirmed absent.
- mcp-gateway auth: OAuth 2.1 resource-server mode (RFC 9728) against Entra ID or any OIDC provider; static per-role bearer tokens (`MCP_TOKENS_ADMIN/_EDITOR/_VIEWER`); a self-hosted OAuth authorization-server "DCR facade" (RFC 8414 metadata + RFC 7591 dynamic client registration) that lets a client connect with just a URL and no pre-provisioned client ID; rotating refresh tokens with family revocation on replay — [README via WebFetch](https://github.com/mspstack/mcp-gateway); release notes confirm "OAuth client attribution and DCR redirect-URI allowlist gating" (v0.19.0) and "Auto-cleanup of abandoned OAuth clients after 30 days" (v0.19.1) — [Releases](https://github.com/mspstack/mcp-gateway/releases).
- mcp-gateway access control: role-based (viewer/editor/admin + custom roles), tool-tier annotation (read/write/destructive), per-tool allow/deny overrides re-checked at call time, and network ACLs bound to tool tiers and "browser surfaces" (v0.20.0) — [README via WebFetch](https://github.com/mspstack/mcp-gateway); [Releases](https://github.com/mspstack/mcp-gateway/releases).
- mcp-gateway hot-reload confirmed explicitly: "Changes are hot: connected MCP clients get a `tools/list_changed` notification" when an admin disables, deletes, or adds an upstream server from the UI — no gateway restart — [docs/ui-guide.md](https://raw.githubusercontent.com/mspstack/mcp-gateway/main/docs/ui-guide.md).
- mcp-gateway per-user credentials: "Let the Add-server form declare per-user credentials" shipped in release v0.21.0 (2026-09-28) — [commit history](https://github.com/mspstack/mcp-gateway/commits/main).
- mcp-gateway observability: a new "Usage tab with per-user tool-call statistics" shipped in v0.22.0 (2026-10-12); no further audit-log/retention detail found in the fetched docs — [commit history](https://github.com/mspstack/mcp-gateway/commits/main). Dedicated audit-logging documentation was not located.

### Inferences
- mcp-gateway's auth/RBAC feature set (OAuth 2.1 + DCR + tiered roles + network ACLs) looks purpose-built for multi-client, multi-tenant MSP use, which is heavier than most home-lab setups need but directly answers "per-client/role-based access control" and "hot-reload" — both confirmed, where McpManager leaves hot-reload unconfirmed.
- McpManager's logging (per-call parameters/response/timing with a live viewer) is more concretely documented as an audit trail than anything found for mcp-gateway, where only a usage-stats tab is confirmed and no request/response audit log was located.

### Gaps
- Whether McpManager actually requires a restart to pick up a newly added upstream server was not confirmed either way in available docs — flagged as unresolved, not assumed.
- No detailed audit-log/retention documentation was found for mcp-gateway beyond the new per-user usage-stats tab.

## LONG-LASTING — maintainer, activity, stars, releases

### Takeaway
Both are solo-developer projects with modest followings, but their current trajectories diverge sharply as of November 2026: McpManager's `main` branch has had no commits since 2026-05-27 (~5+ months stale) and no release since v1.1.2 (2026-05-16), while mcp-gateway is releasing roughly weekly, with its latest tag v0.22.0 dated 2026-10-12 — active within the last month.

### Cited Findings
- McpManager: 18 stars, 5 forks, 10 open issues, MIT license, created 2026-02-26 — [GitHub API](https://api.github.com/repos/daniel3303/McpManager).
- McpManager contributors: daniel3303 (453 contributions, effectively solo), dependabot[bot] (7 contributions) — [GitHub API](https://api.github.com/repos/daniel3303/McpManager/contributors).
- McpManager's last commit on `main` was 2026-05-27 ("chore: add glama.json…"); its last tagged release is v1.1.2, published 2026-05-16 — [commit history](https://api.github.com/repos/daniel3303/McpManager/commits), [Releases](https://github.com/daniel3303/McpManager/releases). The repo's `pushed_at` API field shows 2026-08-13, but the only branches besides `main` are seven open Dependabot dependency-bump branches, which can advance `pushed_at` without any change landing on `main` — [branches list](https://api.github.com/repos/daniel3303/McpManager/branches). This reconciles an initial discrepancy between the two dates.
- McpManager release history: v1.0.0 (2026-02-28, initial stable) → v1.1.0 (2026-05-14) → v1.1.1 (2026-05-15, Docker build fix) → v1.1.2 (2026-05-16) — four releases in under 3 months, then nothing since — [Releases](https://github.com/daniel3303/McpManager/releases).
- mcp-gateway: 1 star, 1 fork, 13 open issues, MIT license, created 2026-07-09 under the GitHub organization account "mspstack" — [GitHub API](https://api.github.com/repos/mspstack/mcp-gateway).
- mcp-gateway contributors: selic (24 contributions) is the only listed contributor — [GitHub API](https://api.github.com/repos/mspstack/mcp-gateway/contributors). The "mspstack" GitHub org has no `company` field set, no description, and only 4 public repos, created 2026-07-16 — i.e., it reads as a solo developer's project/brand umbrella, not a verified funded company, based on available public GitHub metadata — [GitHub API](https://api.github.com/orgs/mspstack).
- mcp-gateway's own README attributes the project to "Eugene Samotija (@selic), defency.net" as an individual developer, with mcp-gateway positioned as part of an "MSPStack family" of MCP tooling for Managed Service Providers — [README via WebFetch](https://github.com/mspstack/mcp-gateway).
- mcp-gateway release cadence (tag list, newest first): v0.22.0 (2026-10-12) → v0.21.1 (2026-10-05) → v0.21.0 (2026-09-28) → v0.20.2 (2026-09-11) → v0.20.1/v0.20.0 (2026-08-28) → v0.19.1/v0.19.0 (2026-08-28) → v0.18.0 (2026-08-27) → v0.17.0 (2026-08-20) — roughly weekly releases since August 2026 — [Tags API](https://api.github.com/repos/mspstack/mcp-gateway/tags), [commit history](https://github.com/mspstack/mcp-gateway/commits/main).
- mcp-gateway's most recent commit is 2026-10-12 ("Release v0.22.0" / new per-user usage-stats tab) — within the last month of the November 2026 research date — [commit history](https://github.com/mspstack/mcp-gateway/commits/main).

### Inferences
- Despite having far fewer stars (1 vs. 18) and a much younger repo (created July 2026 vs. February 2026), mcp-gateway shows materially stronger recent-activity signal than McpManager: weekly releases through mid-October 2026 vs. McpManager's silence since May 2026. Star count is a poor proxy for maintenance health here.
- Neither project shows evidence of corporate backing/funding; "mspstack" is best read as a solo developer's brand for a family of MSP-focused MCP tools, not a company, based on the empty `company` field and single contributor.
- McpManager's ~5-month commit silence combined with 10 open issues (vs. 2 reported in an earlier, apparently less current fetch) is a soft abandonment signal worth flagging, though not definitive — a single maintainer could resume at any time, and the project did ship 4 releases in its first 3 months before going quiet.

### Gaps
- Could not determine why GitHub's `pushed_at` for McpManager (2026-08-13) postdates its last `main` commit (2026-05-27) beyond the Dependabot-branch explanation above; GitHub's exact accounting wasn't independently verifiable within budget.
- No issue-response-time data (how quickly maintainers triage/close issues) was gathered for either project — only open-issue counts.

## FAST — deterministic proxy architecture, benchmarks

### Takeaway
Both projects describe themselves architecturally as deterministic HTTP proxies/routers with no LLM reasoning in the request path, but neither publishes any latency or throughput benchmark numbers.

### Cited Findings
- McpManager is described as "a self-hosted MCP proxy and aggregation platform that manages multiple upstream MCP servers and exposes them through a single unified endpoint" — proxy/aggregation framing, no mention of LLM-based routing or reasoning — [README via WebFetch](https://github.com/daniel3303/McpManager).
- No latency/performance benchmarks are present in McpManager's README — [README via WebFetch](https://github.com/daniel3303/McpManager).
- mcp-gateway is described as "one endpoint that federates your MCP servers, with roles, tool tiers, and secrets that never reach the client" and documents "anti-passthrough enforcement: inbound tokens resolve identity only" — consistent with a deterministic auth/routing proxy rather than an LLM-mediated one — [GitHub API description](https://api.github.com/repos/mspstack/mcp-gateway); [README via WebFetch](https://github.com/mspstack/mcp-gateway).
- No latency/performance benchmarks are present in mcp-gateway's README or the docs files reviewed (`ui-guide.md`, `standalone-secrets.md`) — [docs via WebFetch](https://raw.githubusercontent.com/mspstack/mcp-gateway/main/docs/ui-guide.md).

### Inferences
- Both are plain relay/router implementations (ASP.NET Core backend for McpManager; Node.js backend for mcp-gateway) with no indication of an LLM in the hot path — the "FAST" criterion is architecturally satisfied for both, but neither backs it with measured numbers.

### Gaps
- Zero published benchmark data (p50/p99 latency, throughput) exists for either project in any source checked. This should be treated as "unverified/unmeasured," not "slow" — absence of data, not evidence of a problem.

## CROSS-CLIENT — Claude Code, Gemini/Antigravity, ChatGPT, custom upstream registration

### Takeaway
Both projects document Claude-Code-style config (URL + Bearer-token headers), which should also work for a generic Python agent and likely Antigravity/Gemini-style MCP clients since they use the same transport shape — but neither project's docs explicitly mention Gemini/Antigravity by name. mcp-gateway is the only one of the two with features purpose-built for ChatGPT's remote-connector OAuth flow (DCR facade); ChatGPT compatibility for McpManager is undocumented. Both support registering an arbitrary custom HTTP/SSE upstream, and for mcp-gateway this works independent of OpenBao/secret storage.

### Cited Findings
- McpManager documented client config (generic MCP JSON, works for Claude Code, Cursor, Windsurf per its docs):
  ```json
  {
    "mcpServers": {
      "mcpmanager": {
        "url": "http://localhost:5057/mcp",
        "headers": { "Authorization": "Bearer YOUR_API_KEY" }
      }
    }
  }
  ```
  — [README via WebFetch](https://github.com/daniel3303/McpManager). No Gemini/Antigravity or ChatGPT-specific instructions were found in the README.
- McpManager custom-upstream registration: the "Create Server" UI supports "multi-transport support" — HTTP/SSE for remote servers (Bearer/API key/Basic auth), stdio for local CLI tools (env vars), and OpenAPI-spec-to-MCP conversion; exact UI field-by-field steps are not spelled out in the README, only the feature list — [README via WebFetch](https://github.com/daniel3303/McpManager).
- mcp-gateway documented Claude Code CLI config:
  ```
  claude mcp add --transport http mspstack http://localhost:3100/mcp \
    --header "Authorization: Bearer <token>"
  ```
  plus JSON config snippets for Desktop/Cursor/VS Code — [README via WebFetch](https://github.com/mspstack/mcp-gateway). No Gemini or Antigravity-specific example was found.
- mcp-gateway custom-upstream registration, exact config syntax from `mspstack.config.example.json`:
  ```json
  { "id": "itglue", "namespace": "itglue", "transport": "http",
    "url": "http://localhost:3000/mcp",
    "headers": { "Authorization": "Bearer ${ITGLUE_GATEWAY_TOKEN}" } }
  ```
  (a second example registers a ConnectWise upstream at `http://localhost:3001/mcp` the same way) — [mspstack.config.example.json](https://raw.githubusercontent.com/mspstack/mcp-gateway/main/mspstack.config.example.json). The admin UI alternatively supports "add any MCP server by URL, npm package (npx), or Docker image" with a "preflight-test before saving" step — [README via WebFetch](https://github.com/mspstack/mcp-gateway).
- mcp-gateway secret storage does not gate plain custom-upstream registration: credentials can be plain `${VAR}` env-var references with OpenBao skipped entirely — "the smallest deployment is just tokens + env vars" — [README via WebFetch](https://github.com/mspstack/mcp-gateway); confirmed in [docs/standalone-secrets.md](https://raw.githubusercontent.com/mspstack/mcp-gateway/main/docs/standalone-secrets.md).
- mcp-gateway's OAuth/DCR design is explicitly aimed at URL-only remote-client connection: "the gateway hosts its own OAuth authorization server facade (RFC 8414 metadata + RFC 7591 dynamic client registration + rotating refresh tokens), brokering user sign-in to your IdP; `claude mcp add <url>` connects with no pre-provisioned client id — URL only" — and this is the same mechanism needed for ChatGPT's remote-connector OAuth flow (ChatGPT's developer-mode connector setup is "paste the URL, set authentication to OAuth") — [WebSearch summary of README](https://github.com/mspstack/mcp-gateway). Note: this is the project's own claim about general OAuth/DCR compatibility; no McpManager-style explicit "tested with ChatGPT" statement, release note, or screenshot confirming an actual successful ChatGPT connector pairing was found for mcp-gateway — treat as "architecturally designed for it," not "confirmed working with ChatGPT in practice."
- No explicit mention of ChatGPT compatibility — positive or negative — was found anywhere in McpManager's README, docs, or releases.

### Inferences
- For Mark's four target clients: Claude Code and a generic Python HTTP+headers agent are well-supported by both projects' documented config shape (URL + Bearer header). Gemini/Antigravity compatibility is a reasonable inference (same MCP-over-HTTP transport) but is unverified by either project's own docs — true for both tools equally.
- ChatGPT's remote-connector requirement for either OAuth or specific header-based auth favors mcp-gateway, which ships a purpose-built OAuth 2.1 + DCR facade aimed at exactly this "URL-only" client pattern; McpManager's documented auth (Bearer/API-key/Basic) could still work with ChatGPT only if ChatGPT's connector supports static bearer-token auth (not confirmed either way in sources checked).
- Custom self-hosted HTTP/SSE upstream registration is well-documented with exact syntax for mcp-gateway (JSON config shown above) and only described at a feature-list level (not exact UI steps) for McpManager.

### Gaps
- Neither project's docs explicitly confirm a tested, working ChatGPT remote-connector pairing (as opposed to architectural compatibility claims) — this should be verified hands-on before relying on it.
- Neither project documents Gemini or Antigravity by name; compatibility with those clients is inferred from standard MCP-over-HTTP transport support, not confirmed in either project's own documentation.
- Exact step-by-step UI screens for adding a custom upstream in McpManager (as opposed to the feature list and JSON-config approach for mcp-gateway) were not available in the README; would need direct review of `docs/screenshots` or a live instance to confirm.
