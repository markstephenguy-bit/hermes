# Session Seed — Cognee Cloud migration, handed off due to Claude usage limits

This replaces the previous seed in full. The prior secrets-over-MCP design
discussion (Vaultwarden replacement, `mcp.markstephenguy.com` gateway) is
**parked, not abandoned** — it's still genuinely unresolved, just not the
active thread. Find it via `git log -p -- NEXT_SESSION.md` if it needs to be
picked back up. If you're an agent picking this up cold, read this whole
file before touching anything. If you're Mark pasting this into a new chat,
paste the whole file as your opening message.

## Recommendation: use Codex/ChatGPT, not Antigravity, if you have a choice

Codex has been directly, repeatedly verified working with everything below —
real tool calls, real answers, multiple times. Antigravity's connection was
*configured* but **never once verified working** — there's no CLI path to
test it headlessly, it's a GUI Electron app. Picking this up in Antigravity
means debugging an untested integration from zero with no empirical
baseline; picking it up in Codex means building on a known-good foundation.
If Mark specifically wants Antigravity's connection verified, that's a
smaller side-task any agent can do (or delegate), not a reason to make it the
primary vehicle for this handoff.

## What changed and why

Mark was running Cognee self-hosted on `fileserver` (Postgres+pgvector,
Neo4j, local LM Studio on `w_workstation` for LLM extraction) as the
replacement for a decommissioned Graphiti setup. Confirmed via Salt
(`nvidia-smi`, not raw SSH — `w_workstation` is a Windows box, raw SSH
probing caused a lockout once before, see standing rules) that
`w_workstation`'s GPU was thermally throttling under sustained extraction
load: 92-94°C, "SW Thermal Slowdown" active, clock dropped to 46-51% of max
(960-1455MHz vs 2100MHz max, 1560MHz rated). Mark decided self-hosting isn't
sustainable on this hardware and pivoted to **Cognee Cloud** (hosted SaaS,
`cognee.ai`) instead, keeping the already-validated decision that Cognee
itself (the engine) is better than Graphiti/Hindsight at graph/relationship
extraction. Cooling itself was separately flagged for Mark to revisit later —
don't assume it's closed just because the pivot made it moot for Cognee's
workload specifically.

## What's DONE and verified — don't redo this

- **Cognee Cloud account exists.** Credentials stored at
  `~/.config/cognee-cloud/credentials.env` (mode 0600) on **both** this
  laptop and `hermes-vps`. Contains `COGNEE_CLOUD_API_BASE_URL`,
  `COGNEE_CLOUD_TENANT_ID`, `COGNEE_CLOUD_USER_ID`, `COGNEE_CLOUD_API_KEY`,
  `COGNEE_CLOUD_MCP_URL`. **Never print this key in chat or commit it
  anywhere** — don't ask Mark to repaste it, it's already stored.
- **Key discovery**: Cognee Cloud's *hosted MCP endpoint*
  (`https://mcp.aws.cognee.ai/mcp`) requires OAuth 2.1 + dynamic client
  registration and explicitly does not accept static API keys. This caused
  real pain: Codex hit a reproducible internal caching bug with
  OAuth-registered servers (stale state even after a full app restart);
  Claude Code's OAuth login needs a real interactive TTY that tool-calling
  can't provide; Hermes's headless VPS can't complete a browser OAuth flow
  either.
- **Solved it** by building `scripts/cognee_cloud_mcp.py` (committed to this
  repo) — a thin local stdio MCP wrapper, same shape as the existing
  `scripts/hindsight_mcp.py`, that talks to Cognee Cloud's plain **REST API**
  (`/api/v1/remember`, `/api/v1/recall`, `/api/v1/datasets/status`,
  `/api/v1/datasets/`) using the static `X-Api-Key`/`X-Tenant-Id` headers,
  and re-exposes it as an ordinary unauthenticated local MCP server. No
  OAuth needed anywhere with this approach.
  - **Important implementation detail**: `/api/v1/remember` is *async* on
    Cognee Cloud — it returns `{"status":"running","dataset_id":...}`
    immediately, unlike the old self-hosted MCP tool which blocked until
    done. The wrapper's `remember()` tool polls
    `/api/v1/datasets/status?dataset=<id>` every 3s (300s cap) until
    `DATASET_PROCESSING_COMPLETED`/`ERRORED`, to keep the same "done when it
    returns" contract everything else expects. Pass `background=True` to
    skip the poll if fire-and-forget is wanted instead.
- **Registered and tested:**
  | Client | Where | Status |
  |---|---|---|
  | Codex (global) | `~/.codex/config.toml` | ✅ verified, real `codex exec` call, correct answer |
  | Codex (repo) | `.codex/config.toml` | ✅ same entry, same binary |
  | Hermes | `hermes-vps` `~/.hermes/config.yaml` | ✅ verified via real `hermes_chat` call |
  | Claude Code (global) | `~/.claude.json` | Registered, shows "✔ Connected" — never live-tested (CLI can't auth headlessly outside the parent app) |
  | Claude Code (repo) | `.mcp.json` | Same entry, same caveat |
  | Antigravity | `~/.gemini/config/mcp_config.json` | Entry written — **never verified**, needs a human or an agent running inside Antigravity itself |
- **Hermes-specific deployment notes**: `hermes-vps` has no `uv`/`pipx`/venv
  access without `sudo` (no root available, password required). Fixed by
  `pip install --user --break-system-packages fastmcp httpx` — user-level
  only, nothing touched system-wide. Script deployed to
  `~/.hermes/mcp_servers/cognee-cloud/cognee_cloud_mcp.py`, credentials at
  the same `~/.config/cognee-cloud/credentials.env` path as the laptop.
  Registered via `hermes mcp add cognee --command python3 --args ...`. The
  gateway needed `systemctl --user restart hermes-gateway` to pick up the
  new tool — it briefly hung "deactivating" on a stuck subprocess from an
  earlier timeout, which cleared on its own after ~90s. If this happens
  again: check `systemctl --user status hermes-gateway` for a hung child
  process under the cgroup and kill it directly rather than waiting forever.
- **Full consistency swept and confirmed**: zero stale references anywhere
  to either the old self-hosted URL (`http://192.168.40.2:8767/mcp` /
  WireGuard `10.60.0.2:8767/mcp`) or the abandoned OAuth cloud URL
  (`https://mcp.aws.cognee.ai/mcp`) across all 5 clients' configs.
- **Pricing researched, no need to redo**: Cognee Cloud free tier = 10M
  tokens prepaid, $1/1M tokens after, $5/mo per extra workspace. The full
  migration below is estimated well under $1.50 — almost certainly inside
  the free tier.

## What's stopped but NOT deleted — reversible, leave alone unless asked

- Self-hosted Cognee Docker stack on `fileserver`
  (`/home/mark/services/cognee/`): all 5 containers (`cognee`, `cognee-mcp`,
  `cognee-ui`, `cognee-postgres`, `cognee-neo4j`) stopped via
  `docker compose stop` — **not** `down -v`. All data/volumes intact,
  restartable with `docker compose up -d`. **Don't fully decommission this
  until the Cognee Cloud migration below is verified complete** — it's
  currently the only copy of a partial migration (see below).

## What's genuinely NOT done — this is the real remaining work

1. **The actual Hindsight → Cognee Cloud data migration never completed.**
   A full raw export of Hindsight's `hermes` bank (3,213 facts, via
   paginated `GET http://192.168.40.100:8888/hindsight/v1/default/banks/hermes/memories/list?limit=500&offset=N`,
   7 pages) was pulled and saved locally during the prior session at
   `/tmp/claude-1000/-home-mark-projects-Hermes/6f2485ca-dd68-457e-93b2-687705307196/scratchpad/hindsight_dump/page_*.json`.
   **That path is a different agent's ephemeral scratchpad and will almost
   certainly not exist in a fresh session** — check cheaply first, but plan
   to re-pull the export fresh using the same method if it's gone (it's a
   simple paginated GET, no auth needed on the LAN).
2. A partial migration attempt (192 of 241 planned batches, grouped by
   Hindsight's `document_id`) was run against the **self-hosted** instance
   before the Cloud pivot happened. That data exists only in the now-stopped
   self-hosted Postgres/Neo4j volumes — **not** in Cognee Cloud. Simplest
   path: don't bother recovering it from the stopped containers — just redo
   the full migration straight into Cognee Cloud from a fresh Hindsight
   export, same batching strategy (group by `document_id`, chunk the ~1,407
   facts with no `document_id` into groups of ~50), using
   `cognee_cloud_mcp.py`'s `remember()` tool into a dataset (suggest calling
   it `hindsight_migration` again for continuity). Include the same
   "migrated from Hindsight, verify time-sensitive claims" framing note used
   last time, and the explicit fact that Cognee replaced Graphiti (and now
   Cognee Cloud replaced self-hosted Cognee) so future recall doesn't
   present stale snapshots as current.
3. The `infrastructure` dataset (6 migrated-from-Graphiti snapshot files +
   the "Cognee replaced Graphiti" fact) was ingested into the **self-hosted**
   instance only — also needs re-ingesting into Cognee Cloud. Source files
   are untouched at `/home/mark/services/cognee/imports/infra-2026-11-14-*.txt`
   on `fileserver`.
4. Antigravity's connection needs real verification (open the app, find
   Cognee under its MCP/Integrations panel, confirm it connects and
   discovers tools — `remember`, `recall`, `list_datasets`).
5. Claude Code's connection would benefit from one live conversational test
   too, if there's a convenient way to do it.
6. Only after 2 and 3 are verified complete in Cognee Cloud: decommission
   the self-hosted `fileserver` stack for real (`docker compose down -v`),
   mirroring exactly how Graphiti was torn down earlier this same overall
   effort.
7. Test-artifact cleanup: two throwaway datasets exist in Cognee Cloud from
   wrapper validation (`cognee_cloud_validation`, `cognee_cloud_timing_test`)
   — fine to leave or delete, they're not real content.

## Standing rules to carry forward

- **Use Salt for anything touching `w_workstation`** (the `infra` MCP
  server's `salt_minion_status`/`salt_run` tools, or `hermes mcp`) — never
  raw SSH probing against it. It's a Windows box with no configured key
  auth; a prior raw-SSH attempt caused repeated auth failures and a lockout.
- **Never print or commit the Cognee Cloud API key.** It's already stored
  securely (0600, outside any git repo) on both machines that need it.
- **Memory upkeep and git upkeep are the agent's job, not Mark's**, per this
  repo's `CLAUDE.md` — retain decisions to Hindsight (bank `hermes`) as they
  happen, commit and push as work lands, no need to ask first.
- **Verify every registration with a real tool call before calling it
  done** — a config that "looks right" isn't enough. This exact discipline
  caught Codex's OAuth caching bug, a missing `notifications/initialized`
  message in a raw stdio test harness, and the async-vs-sync `remember()`
  semantics mismatch, all of which would have silently produced wrong
  results otherwise.
- Hindsight itself (bank `hermes`) is untouched and still the active, native
  memory system for Hermes and the harnesses — this whole effort only ever
  concerned the separate infrastructure-knowledge-graph role, never
  Hindsight's own role. Don't let "migrate Hindsight's content into Cognee"
  get confused with "replace Hindsight."
