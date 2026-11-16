# ToolHive Virtual MCP Server (vMCP) vs. SidPad03/unified-mcp-gateway

Research date: November 2026. Scope: evaluate both self-hosted MCP gateway/aggregation
projects against 5 criteria (Singular, Powerful, Long-lasting, Fast, Cross-client) for a
home-lab user who wants one container fronting multiple MCP capabilities — including
custom self-written HTTP-transport MCP servers — reachable by Claude Code, Antigravity
(Gemini), ChatGPT's remote MCP connector, and a generic Python agent that only knows
URL+headers.

## SINGULAR — ToolHive vMCP: is it really one container?

### Takeaway
In its newer **local CLI mode** (no Kubernetes), vMCP runs as a single foreground Go
process with an embedded SQLite store for its optimizer — no external Postgres/Redis
required for vMCP itself. However, vMCP is an *aggregator over backends*: those backend
MCP servers are expected to already be running as ToolHive-managed workloads (each
typically its own container via `thv run`), so "one container total" only holds if you
count vMCP's own process alone, not the full picture of everything it fronts.

### Cited Findings
- "You no longer need a Kubernetes cluster to try vMCP. With the new local CLI mode, you can take the MCP servers you already run on your machine and present them to your AI client as a single endpoint." — [Stacklok updates, 2026-04-27](https://docs.stacklok.com/toolhive/updates/2026/04/27/updates)
- `thv vmcp` has three subcommands: `init` (generate starter config), `serve` (start the Virtual MCP Server), `validate` (validate config) — described as running "locally without Kubernetes." — [thv vmcp CLI reference](https://docs.stacklok.com/toolhive/reference/cli/thv_vmcp)
- Local vMCP architecture doc: runs as "a single foreground process driven by Cobra CLI flags," implemented in Go, ships with every ToolHive release, "requiring no separate Python environment." — [docs/arch/vmcp-local.md, stacklok/toolhive](https://github.com/stacklok/toolhive/blob/main/docs/arch/vmcp-local.md)
- Database: the optimizer uses "FTS5 keyword (SQLite in-process)" for its default tier — no external DB like PostgreSQL required for vMCP itself. Docker/Podman is only invoked optionally for Tier-2 semantic optimization (`--optimizer-embedding`, which spins up a Text Embeddings Inference container) — not required for basic aggregation. — [docs/arch/vmcp-local.md](https://github.com/stacklok/toolhive/blob/main/docs/arch/vmcp-local.md)
- vMCP aggregates backends from "a ToolHive group" — i.e., MCP servers already registered/running as ToolHive workloads — via `thv vmcp serve --group <name>` (auto-discovery) or a generated `vmcp.yaml` with one `backends` entry per workload. — [docs/arch/vmcp-local.md](https://github.com/stacklok/toolhive/blob/main/docs/arch/vmcp-local.md)
- The Kubernetes deployment mode runs vMCP via a `VirtualMCPServer` custom resource under the ToolHive Operator — a separate, heavier path not needed for a home-lab single-host setup. — [vMCP concepts](https://docs.stacklok.com/toolhive/concepts/vmcp)

### Inferences
- For a home-lab "one container" goal, the realistic unit is "one extra lightweight container/process for vMCP itself, plus however many containers you already run for your backend MCP servers (including custom ones)" — not literally one container for the entire capability set, but also not requiring a bundled database/dashboard stack the way unified-mcp-gateway does.

### Gaps
- Documentation does not state whether a custom backend MCP server must be wrapped/registered as a "ToolHive workload" (via `thv run`) or whether an arbitrary external streamable-HTTP/SSE endpoint (not managed by ToolHive) can be added directly as a vMCP backend in local mode — the local-mode YAML backend-entry syntax itself was not shown in the fetched docs. This is a material gap for the user's "custom self-written HTTP-transport MCP servers" requirement and should be verified directly against `thv vmcp init` output or the vmcp.yaml schema before committing to this tool.

## SINGULAR — unified-mcp-gateway: is it really one container?

### Takeaway
No — confirmed directly from the project's own `docker-compose.yml`: it requires **three** containers (PostgreSQL, the Rust/Axum gateway server, and a separate React dashboard), contradicting a "single container" setup. A fourth component (a macOS-only desktop "Agent" app) exists for tunneling local stdio servers in, but is not a Docker container.

### Cited Findings
- Direct read of `docker-compose.yml` in the repo defines exactly three services: (1) `postgres` — image `postgres:16-alpine`, with a health check and a named volume `postgres_data`, no externally exposed port; (2) `mcp-gateway-server` — image `sidpad03/mcp-gateway-server:latest`, port `3200:3200`, depends on postgres being healthy, requires a `JWT_SECRET` env var; (3) `mcp-gateway-dashboard` — image `sidpad03/mcp-gateway-dashboard:latest`, port `8080:80`, depends on the server being healthy. — [docker-compose.yml, sidpad03/unified-mcp-gateway](https://github.com/sidpad03/unified-mcp-gateway/blob/main/docker-compose.yml)
- The author's own announcement post describes the same three-part architecture: "(1) MCP Gateway Server (Rust/Axum + PostgreSQL), (2) MCP Gateway Dashboard (React/TypeScript), (3) MCP Gateway Agent (Rust)," with Docker Compose as the deployment method. — [dev.to/sidpad03](https://dev.to/sidpad03/i-built-an-open-source-security-gateway-for-mcp-because-the-ecosystem-desperately-needs-one-4dkc)
- A fourth, non-containerized component — "MCP Gateway Agent" (Rust + SwiftUI, macOS only, installed via `brew install --cask sidpad03/tap/mcp-gateway-agent`) — bridges local stdio MCP servers to the gateway over authenticated WebSocket, avoiding inbound ports. This is irrelevant for a Linux home-lab host running HTTP-transport servers, which can register directly without the Agent. — [GitHub README summary](https://github.com/sidpad03/unified-mcp-gateway)

### Inferences
- The project's own quick-start README tagline implicitly already matches the user's own prior read ("gateway, dashboard, and PostgreSQL database") — this is now directly confirmed against the actual compose file, not just marketing copy. For a user who only wants to add their own HTTP-transport MCP servers (no stdio bridging needed), the macOS Agent is skippable, but the 3-container Postgres+server+dashboard stack is mandatory to run the gateway at all — there is no documented all-in-one single-container image.

### Gaps
- Not verified: whether the dashboard is strictly required to be running for the gateway/API (port 3200) to function, or whether it could be omitted/stopped after initial admin setup while leaving the server+postgres running (i.e., could a user drop to 2 containers in practice). The docker-compose health-check chain (`dashboard` depends on `server` depends on `postgres`) suggests dashboard is a client of the server, not vice versa — but this wasn't explicitly confirmed in docs.

## POWERFUL — ToolHive vMCP: auth, RBAC, audit, dynamic backends

### Takeaway
vMCP includes an embedded OAuth 2.0/2.1 Authorization Server with Cedar-based policy enforcement and multi-IdP federation (GitHub, Google, Okta, etc.) — materially more sophisticated than a simple bearer-token proxy — but the documentation fetched does not confirm plain static bearer-token/API-key auth as an option for *clients connecting to* vMCP (OAuth 2.1 appears to be the primary/required client-facing auth), nor does it give a definitive answer on hot-adding backends without restart.

### Cited Findings
- "Clients authenticate to vMCP using OAuth 2.1 authorization as defined in the MCP specification." The embedded authorization server supports "multiple upstream identity providers (such as GitHub, Google, or Okta)." — [vMCP concepts](https://docs.stacklok.com/toolhive/concepts/vmcp)
- "The Virtual MCP Server includes an embedded OAuth 2.0 Authorization Server, which brokers authentication between MCP clients and your identity provider and enforces access control through Cedar policies." — [WebSearch synthesis of docs.stacklok.com/toolhive/guides-vmcp/intro](https://docs.stacklok.com/toolhive/guides-vmcp/intro.md)
- vMCP "aggregates tools from multiple backend MCP servers and resolves naming conflicts, and can create multi-step workflows that span multiple backend MCP servers." It supports "centralized authentication, routing, or tool optimization." — [vMCP guides index](https://docs.stacklok.com/toolhive/guides-vmcp/)
- Separately (not vMCP-specific but ToolHive-wide): ToolHive can connect to *remote, hosted* MCP servers "with OAuth, OIDC, and bearer token authentication," including "native OAuth/OIDC support and dynamic client registration." — [Stacklok blog, "Seamless remote MCP server support with ToolHive"](https://stacklok.com/blog/seamless-remote-mcp-server-support-with-toolhive/)
- Audit: the vMCP concepts page references "a complete audit trail" for access-control changes and links to a separate Observability doc, but the fetched excerpt did not detail log format/retention/export mechanics. — [vMCP concepts](https://docs.stacklok.com/toolhive/concepts/vmcp)
- Dynamic backend management: a live GitHub issue shows this is an active, imperfect area — "vMCP: Terminate() retains backend connections in the node-local cache until eviction" and a related note that ToolHive v0.48.0 "did not update an already-open MCP session after backend removal and emitted no `tools/list_changed`" (open client sessions don't get live-notified of backend removal, even if the gateway itself is reconfigured). — [GitHub issue #6762, stacklok/toolhive](https://github.com/stacklok/toolhive/issues/6762)

### Inferences
- vMCP's security model is built around OAuth-federated, policy-as-code (Cedar) access control rather than a simple static bearer token — powerful for an enterprise/team setting, but this may add setup complexity for a single home-lab user who just wants a static bearer token across clients. Whether a simpler static-token mode exists for vMCP specifically (as opposed to ToolHive's general remote-MCP-proxy bearer-token support) was not confirmed.
- Backend add/remove without a full process restart appears to be supported in principle (ToolHive's broader "add/disable/remove workloads behind a stable gateway URL" capability), but there's a documented rough edge where already-connected client sessions don't get notified of changes — practically meaning a client may need to reconnect/refresh its tool list after a backend change, even if the gateway process itself didn't restart.

### Gaps
- Could not confirm from primary docs whether vMCP supports simple static bearer-token or API-key auth as an alternative to full OAuth 2.1 for low-stakes home-lab use — this needs direct verification against `thv vmcp init`'s generated config schema or the auth section of the vMCP guide not fully captured here.
- Exact audit log format, retention, and export mechanism not confirmed (only that an audit trail concept exists and a separate Observability doc is linked).

## POWERFUL — unified-mcp-gateway: auth, RBAC, audit, dynamic backends

### Takeaway
The project's own README and author blog post make detailed, specific claims — JWT + API-key auth, role-based access control (owner/operator/viewer plus custom roles), a priority-ordered glob-pattern policy engine, automatic tool risk classification, and per-call audit logging with redaction — and these are **self-reported by the (effectively solo) author**, not independently verified by a third party or security audit in the sources found.

### Cited Findings
- Auth: "JWT + API Key authentication; API keys prefixed with `mcpgw_` and SHA-256 hashed." — [GitHub README summary](https://github.com/sidpad03/unified-mcp-gateway)
- Per-application scoping: "JWT + API key auth" with separate credentials "for different clients like Claude and Cursor." — [dev.to/sidpad03 blog post](https://dev.to/sidpad03/i-built-an-open-source-security-gateway-for-mcp-because-the-ecosystem-desperately-needs-one-4dkc)
- RBAC: "RBAC with built-in owner role and custom role creation"; separately described as "owner, operator, viewer roles" with "tool-level permissions." — [GitHub README](https://github.com/sidpad03/unified-mcp-gateway) and [dev.to post](https://dev.to/sidpad03/i-built-an-open-source-security-gateway-for-mcp-because-the-ecosystem-desperately-needs-one-4dkc)
- Policy engine: "priority-ordered allow/deny rules with glob patterns." — [GitHub README](https://github.com/sidpad03/unified-mcp-gateway)
- Risk classification: tools are "automatically tagged as read, write, admin, destructive, execute, or unclassified." — [GitHub README](https://github.com/sidpad03/unified-mcp-gateway)
- Audit: "Audit Logging records every tool call with configurable redaction." — [GitHub README](https://github.com/sidpad03/unified-mcp-gateway); confirmed again in the author's post: "Audit logging — every tool call recorded" with "configurable payload redaction." — [dev.to post](https://dev.to/sidpad03/i-built-an-open-source-security-gateway-for-mcp-because-the-ecosystem-desperately-needs-one-4dkc)
- Dynamic backends: README lists "Automatic tool namespacing with collision resolution" and a dashboard page for "backends," implying backends can be managed live through the admin UI, but no explicit statement was found confirming add/remove happens *without* restarting the gateway container.
- Observability: "Prometheus metrics at `/metrics`" and dashboard pages for "usage, audit, and metrics." — [GitHub README](https://github.com/sidpad03/unified-mcp-gateway)

### Inferences
- Feature-for-feature, the claimed capability list (RBAC, policy engine, risk classification, audit, Prometheus metrics) is comparably rich to — in some respects (e.g., automatic risk classification) more opinionated than — vMCP's, but it comes from a single-author project's own self-reported README/blog rather than from a company with a security track record. Given this is explicitly a "security gateway," the lack of independent/third-party validation of these claims (e.g., a security audit, CVE history, or academic benchmark naming it specifically) is a meaningful gap for a tool whose entire value proposition is access control and audit trails.

### Gaps
- No independent (non-author) verification of the RBAC/policy/audit claims was found. A related academic paper, "GatewayBench: Unified Capability and Security Evaluation Platform for MCP Gateways" ([arXiv:2610.23449](https://arxiv.org/html/2610.23449)), appeared in search results as benchmarking MCP gateways in general, but it was not fetched/confirmed to include this specific project — flagging as an unconfirmed lead rather than a citable finding.
- No explicit documentation found confirming whether adding/removing a backend MCP server via the dashboard triggers a live reconfiguration versus requiring a gateway restart.

## LONG-LASTING — ToolHive: backing and activity

### Takeaway
ToolHive is backed by Stacklok, a venture-funded (Series A, $17.5M from Accel and Madrona, founded 2023) software-supply-chain-security company with a track record of other real open-source security projects (e.g., Minder, donated to the OpenSSF). The `stacklok/toolhive` repo is extremely active as of the research date — multiple releases per week, including one dated the same day as this research (November 3, 2026).

### Cited Findings
- Stacklok: "a startup focused on enhancing software supply chain security... based in Seattle... founded in 2023... raised $17.5M in funding from Accel and Madrona" in a Series A round (May 17, 2023); more recent investor list also includes Bain Capital Ventures. — [Crunchbase/Tracxn/Dealroom aggregated via WebSearch](https://www.crunchbase.com/organization/stacklok)
- Stacklok donated its "Minder" open-source supply-chain-security project to the OpenSSF, evidencing a real, pre-existing open-source security track record beyond ToolHive. — [The New Stack](https://thenewstack.io/stacklok-donates-minder-security-project-to-openssf/)
- `stacklok/toolhive` repo: ~2.3k GitHub stars, Apache 2.0 license, Go-based, with linked sibling repos (toolhive-studio desktop UI, toolhive-registry-server, toolhive-catalog, docs-website) indicating an ecosystem rather than a single throwaway repo. — [github.com/stacklok/toolhive](https://github.com/stacklok/toolhive)
- Release cadence (most recent tags found): v0.61.0 (Nov 3, 2026), v0.60.0 (Nov 2, 2026), v0.59.0 (Oct 28, 2026), v0.58.0 (Oct 27, 2026), v0.57.0 (Oct 26, 2026) — i.e., near-daily releases through the research date, with v0.57.0 specifically adding "backend-scoped vMCP authorization," confirming vMCP itself is under active, recent development, not a stale or abandoned feature. — [github.com/stacklok/toolhive/releases](https://github.com/stacklok/toolhive/releases)

### Inferences
- Both the company and the specific vMCP feature are clearly "long-lasting" by the requested criteria: real funded company, independent security track record, very high commit/release velocity continuing right up to the present.

### Gaps
- None material — this criterion is well-supported by primary sources (Crunchbase/funding data is third-party-aggregated rather than a Stacklok primary source, but is standard, non-controversial company-registry data).

## LONG-LASTING — unified-mcp-gateway: backing and activity

### Takeaway
This is a solo/small hobby-scale project by a single GitHub user (SidPad03), built with heavy use of Claude Code as a co-author, with only 16 stars/4 forks, and its most recent commit/release is September 30, 2026 — over a month stale relative to the November 2026 research date, i.e., currently showing no signs of active maintenance.

### Cited Findings
- Commit history shows "two distinct contributors... SidPad03 (repository owner)" and "claude" (listed as a co-author on numerous commits) — i.e., effectively one human author pairing with an AI coding assistant, not a team. — [github.com/sidpad03/unified-mcp-gateway/commits/main](https://github.com/sidpad03/unified-mcp-gateway/commits/main)
- Commit history spans roughly two months of activity, with the earliest visible commit around August 7, 2026 and the most recent on September 30, 2026 ("feat(agent): sign the macOS app with Developer ID and notarize releases"). — [github.com/sidpad03/unified-mcp-gateway/commits/main](https://github.com/sidpad03/unified-mcp-gateway/commits/main)
- Repository metrics: 16 stars, 4 forks, Apache 2.0 license, 81 commits on main. — [github.com/sidpad03/unified-mcp-gateway](https://github.com/sidpad03/unified-mcp-gateway)
- Release tags: Gateway and Agent releases both top out at v1.2.4, dated September 30, 2026; no releases found after that date as of the November 2026 research date. — [github.com/sidpad03/unified-mcp-gateway/releases](https://github.com/sidpad03/unified-mcp-gateway/releases)
- Author's own framing in the announcement post positions it as a personal project seeking community help: described as "looking for feedback and contributors," which the author frames as an "open community model rather than corporate backing." — [dev.to/sidpad03](https://dev.to/sidpad03/i-built-an-open-source-security-gateway-for-mcp-because-the-ecosystem-desperately-needs-one-4dkc)

### Inferences
- By every available signal (star count, contributor count, release cadence stalling for over a month as of the research date), this is a young, low-adoption, single-maintainer project. That doesn't make its engineering wrong, but it is a materially higher long-term-risk bet than ToolHive/Stacklok for a home-lab user who wants something they won't have to re-evaluate or migrate off of in six months.

### Gaps
- Could not confirm whether the project has gone fully dormant or is simply between releases (a >1-month gap is suggestive but not definitive proof of abandonment) — would need to check the repo's Issues/PR activity or a direct `git log` closer to the actual report date to be fully certain.

## FAST — ToolHive vMCP: architecture and overhead

### Takeaway
vMCP's core aggregation/proxying path is architecturally a deterministic router (Go process, local SQLite-backed tool index) with no LLM in the simple proxy path; however, its "composite workflow"/"code mode" feature explicitly introduces an additional execution layer (server-side Starlark scripting to batch multiple backend tool calls) that is a deliberate trade-off of some added processing for fewer round-trips — not a case of "no overhead ever," but also not LLM-based reasoning. No quantitative latency/benchmark numbers were found in primary docs.

### Cited Findings
- "Code mode allows agents [to] submit a single Starlark script that orchestrates many backend tool calls server-side instead of one round-trip per tool" — i.e., the workflow feature trades one extra parse/execute step for fewer network round-trips, which is plausibly a net latency win for multi-tool chains, not a cost center, but is explicitly additional processing beyond pure 1:1 proxying. — [vMCP intro, synthesized via WebSearch from docs.stacklok.com/toolhive/guides-vmcp/intro](https://docs.stacklok.com/toolhive/guides-vmcp/intro.md)
- Composite/multi-step workflows support "parallel execution across systems" with "conditionals, and error handling," and "approval gates" — all deterministic control-flow constructs, not LLM calls. — [vMCP concepts/guides, WebSearch synthesis](https://docs.stacklok.com/toolhive/guides-vmcp/)
- A separate "MCP Optimizer" tutorial exists specifically to "reduce token usage," using an in-process SQLite FTS5 index by default (Tier 1) and an optional embedding-model container (Tier 2, `--optimizer-embedding`) — confirming no LLM reasoning is in the default/basic proxy path, and that even the smarter tool-selection tier uses a local embedding model rather than a general LLM call. — [docs/arch/vmcp-local.md](https://github.com/stacklok/toolhive/blob/main/docs/arch/vmcp-local.md), [MCP Optimizer tutorial](https://docs.stacklok.com/toolhive/tutorials/mcp-optimizer)

### Inferences
- For a user who just wants fast deterministic proxying of tool calls (no workflows), vMCP's base path should behave like a normal reverse-proxy/router with negligible added latency; the workflow/optimizer features are opt-in additions, not something imposed on every request by default.

### Gaps
- No published quantitative latency numbers (e.g., added-ms-per-call) were found for vMCP specifically in Stacklok's own docs or blog. The only latency/benchmark data found in the entire research pass was author-claimed (unified-mcp-gateway's "~15MB binary... starts instantly... handles thousands of concurrent connections") and a general academic benchmark paper (GatewayBench, arXiv:2610.23449) that was not confirmed to include either of these two specific tools — so no apples-to-apples benchmark comparison can be cited.

## FAST — unified-mcp-gateway: architecture and overhead

### Takeaway
Architecturally this is a pure deterministic proxy — Rust + Axum async router with no LLM anywhere in the request path — and the author claims a small (~15MB) binary that "starts instantly" and "handles thousands of concurrent connections," but these are self-reported, unbenchmarked claims with no independent load-test numbers found.

### Cited Findings
- "Built in Rust using Axum for async request handling with minimal overhead, has a ~15MB binary size, starts instantly, and handles thousands of concurrent connections." — [WebSearch synthesis, sourced to dev.to/sidpad03 post](https://dev.to/sidpad03/i-built-an-open-source-security-gateway-for-mcp-because-the-ecosystem-desperately-needs-one-4dkc)
- Prometheus metrics explicitly include "latency histograms" as a built-in observability feature, implying the author intends/expects users to measure their own latency rather than publishing fixed numbers. — [GitHub README](https://github.com/sidpad03/unified-mcp-gateway)
- The gateway's risk-classification and policy-engine steps (glob-pattern allow/deny evaluation) run synchronously in the request path per the architecture description — these are deterministic rule evaluations, not LLM calls, consistent with a "fast proxy" architecture. — [GitHub README](https://github.com/sidpad03/unified-mcp-gateway)

### Inferences
- No LLM reasoning is involved in the hot path for either project — both are legitimately "fast deterministic proxy" architectures by design. The main FAST differentiator between them is less about raw request latency (unconfirmed for both) and more about process-model overhead: vMCP in local mode is one extra Go process layered on top of already-running backend containers, while unified-mcp-gateway requires a 3-container stack (Postgres + Rust server + React dashboard) just to be reachable at all, which is a heavier cold-start/resource footprint even if per-request proxying speed is comparable.

### Gaps
- No independently verified benchmark numbers exist for either tool specifically. The "~15MB binary, starts instantly" claim for unified-mcp-gateway is author-reported and unverified by this research pass.

## CROSS-CLIENT — ToolHive vMCP: client configs and custom upstream registration

### Takeaway
ToolHive publishes a 28+-client compatibility matrix explicitly covering Claude Code (auto-config supported) and documents testing with Gemini CLI and Google Antigravity (which reads `~/.gemini/config/mcp_config.json` globally or `.agents/mcp_config.json` per-project) — directly matching two of the user's four target clients. ChatGPT is explicitly flagged as a problem case: "ChatGPT Desktop only accepts MCP servers over HTTPS" with no command-based config, requiring either a real HTTPS endpoint or an ngrok tunnel (which Stacklok itself warns is a security risk for "unauthenticated, publicly-accessible workloads"). For custom upstream registration, exact Kubernetes-mode YAML syntax for a streamable-HTTP backend was found, but the local-CLI-mode syntax for registering an arbitrary custom host:port server was not located in the docs fetched.

### Cited Findings
- "ToolHive automatically updates the global MCP configuration file whenever you run an MCP server and has been tested with Claude Code, Gemini CLI, and Google Antigravity." — [WebSearch synthesis of docs.stacklok.com client docs](https://docs.stacklok.com/toolhive/reference/client-compatibility)
- Antigravity config path: "`mcp_config.json` — globally at `~/.gemini/config/mcp_config.json`, or per-project at `.agents/mcp_config.json`" — this matches the exact path already in use in this user's own environment per their CLAUDE.md. — [WebSearch synthesis](https://docs.stacklok.com/toolhive/reference/client-compatibility)
- Client compatibility matrix categories found: "Fully Featured" (auto-config + skills) includes Claude Code v1.0.27+, GitHub Copilot (VS Code), Cursor, Cline, Windsurf; "Limited Support" (auto-config only) includes Continue, GitHub Copilot CLI, LM Studio; "Manual Configuration Required" explicitly includes **Claude Desktop** and **ChatGPT Desktop**. — [Client compatibility page](https://docs.stacklok.com/toolhive/reference/client-compatibility)
- ChatGPT: "ChatGPT Desktop 'only accepts MCP servers over HTTPS' and lacks command-based configuration options. The documentation suggests using ngrok tunnels for personal experimentation but explicitly warns this approach creates security risks with unauthenticated, publicly-accessible workloads." — [Client compatibility page](https://docs.stacklok.com/toolhive/reference/client-compatibility)
- For production/shared use (which would cover a proper home-lab HTTPS-fronted setup reachable by ChatGPT's remote connector), ToolHive's own docs recommend vMCP specifically: it provides "proper authentication, per-user OAuth, and policy enforcement" — implying vMCP (with its embedded OAuth 2.1 server) is Stacklok's own answer to exposing a gateway safely to something like ChatGPT's remote connector, rather than the raw ngrok-tunnel workaround. — [Client compatibility page](https://docs.stacklok.com/toolhive/reference/client-compatibility)
- Separately, ToolHive (the broader platform, not vMCP-specific) documents connecting to remote MCP servers with "OAuth, OIDC, and bearer token authentication" and "dynamic client registration" — these are the primitives ChatGPT's remote MCP connector is known to require (OAuth 2.0 or header-based auth), though this page was not confirmed to mention ChatGPT by name. — [Stacklok blog: Seamless remote MCP server support](https://stacklok.com/blog/seamless-remote-mcp-server-support-with-toolhive/)
- Custom upstream registration — Kubernetes-mode `MCPServer` custom resource for a streamable-HTTP backend (exact YAML syntax):
  ```yaml
  apiVersion: toolhive.stacklok.dev/v1beta1
  kind: MCPServer
  metadata:
    name: fetch
    namespace: toolhive-system
  spec:
    image: ghcr.io/stackloklabs/gofetch/server
    transport: streamable-http
    proxyPort: 8080
    mcpPort: 8080
    groupRef:
      name: demo-tools
  ```
  — [vMCP quickstart, synthesized from docs.stacklok.com/toolhive/guides-vmcp/quickstart](https://docs.stacklok.com/toolhive/guides-vmcp/quickstart) — *caveat: this example registers a server ToolHive itself runs from a container image (`spec.image`), not an arbitrary already-running external host:port; it was not confirmed whether this schema supports pointing at an external URL instead of an image.*
- Local-mode client connection: `thv run http://localhost:4483/mcp --name demo-vmcp` registers the vMCP endpoint itself with a client; `thv client setup` performs client auto-configuration. — [vMCP quickstart](https://docs.stacklok.com/toolhive/guides-vmcp/quickstart)

### Inferences
- ToolHive clearly documents and tests against Claude Code and Gemini-family (Antigravity) clients, satisfying 2 of the 4 target clients directly. ChatGPT's remote connector is not a documented first-class target for ToolHive's main CLI/Desktop flows, but vMCP's embedded OAuth 2.1 server is positioned by Stacklok itself as the correct way to expose a gateway to externally-authenticated clients — strongly suggesting vMCP (not plain ToolHive) is the right component for ChatGPT compatibility, though this was not confirmed with a worked example.
- The exact mechanism for adding a fully custom, already-running, arbitrary-host:port streamable-HTTP/SSE MCP server as a vMCP backend (as opposed to one ToolHive itself launches from a container image) remains unconfirmed and should be checked directly before committing — it's plausible given ToolHive's general remote-MCP-server support, but no exact config syntax for "point at my own existing http://myhost:myport/mcp" as a vMCP backend was found in the fetched docs.

### Gaps
- No exact, confirmed config syntax for adding a fully custom/arbitrary external streamable-HTTP or SSE MCP server as a vMCP backend (only the image-based `MCPServer` CRD example, and unconfirmed local-mode YAML backend format).
- No explicit, named confirmation that ChatGPT's remote MCP connector (specifically, as opposed to "ChatGPT Desktop") has been tested against ToolHive/vMCP — the compatibility page discusses ChatGPT Desktop's HTTPS-only requirement but does not explicitly name "remote MCP connector" compatibility status.
- No worked example found of a generic "point at URL + headers" Python agent client connecting to vMCP (the fourth target client type) — plausible given OAuth 2.1/bearer support, but not directly documented for that use case.

## CROSS-CLIENT — unified-mcp-gateway: client configs and custom upstream registration

### Takeaway
The project documents one simple, generic config block compatible with "Claude Desktop, Cursor, and compatible AI clients" (standard `mcpServers` JSON with a URL + `Authorization: Bearer` header) — which is exactly the shape a generic Python agent or Claude Code could consume — but there is no documentation found of Antigravity/Gemini-specific config, and no explicit statement of ChatGPT remote-connector compatibility (ChatGPT typically needs OAuth 2.0, and this project's primary auth is JWT/API-key bearer tokens, which may or may not satisfy ChatGPT's specific connector requirements).

### Cited Findings
- Documented client config example:
  ```json
  {
    "mcpServers": {
      "gateway": {
        "url": "http://localhost:3200/mcp",
        "headers": {
          "Authorization": "Bearer <api_key>"
        }
      }
    }
  }
  ```
  described as supporting "Claude Desktop, Cursor, and compatible AI clients." — [GitHub README, sidpad03/unified-mcp-gateway](https://github.com/sidpad03/unified-mcp-gateway)
- Multi-transport backend support explicitly listed: "stdio, HTTP, SSE, WebSocket agent" — confirming custom self-hosted HTTP-transport or SSE MCP servers are a supported backend type, not just stdio. — [GitHub README](https://github.com/sidpad03/unified-mcp-gateway)
- No exact CLI/API syntax for *registering a specific custom backend* (e.g., `POST /backends` with a JSON body, or a CLI command) was found in the fetched material — only that the dashboard has a "backends" management page and that multi-transport backends are supported in principle.
- No mention of Claude Code, Gemini CLI, or Google Antigravity by name was found anywhere in the project's README, docker-compose, or author blog post.
- No mention of ChatGPT or "remote MCP connector" compatibility was found anywhere in the sources reviewed for this project.

### Inferences
- Because the documented client config is the plain, generic MCP JSON shape (`url` + `headers.Authorization: Bearer <token>`), it is very likely to work out-of-the-box with Claude Code and with a generic Python agent that only knows URL+headers (both consume exactly this shape), even though neither is named explicitly in the docs. Antigravity/Gemini compatibility is unconfirmed but plausible for the same reason (same generic MCP client shape), subject to Antigravity's own config file format (`~/.gemini/config/mcp_config.json`) accepting a bearer-header remote server — not tested here. ChatGPT's remote connector is the least certain: it is commonly understood to require full OAuth 2.0 (not just a static bearer header) for *addable* custom connectors, and no evidence was found that this project implements an OAuth flow for client-facing auth (only JWT/API-key) — this is a plausible compatibility gap, not a confirmed one.

### Gaps
- No explicit documentation or community report confirming unified-mcp-gateway works with Antigravity/Gemini CLI, or with ChatGPT's remote MCP connector specifically — both are inferred-plausible-but-unverified rather than confirmed.
- No exact backend-registration API/CLI syntax (as opposed to "there's a dashboard page for it") was found for adding a custom streamable-HTTP/SSE server as an upstream.
