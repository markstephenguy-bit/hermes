# Capability Parity: Hermes vs. Claude Code

Mark is deliberately shifting day-to-day AI-harness usage from Claude Code
to Hermes (stated 2026-10-28) — CC becomes an occasional fallback, not the
default. This doc is the working model for that transition: what Claude
Code can do, what Hermes can actually do *today* (live-verified where
possible, not just configured-but-untested), and what to build/restore/
harden to close the gap. Treat this as a living doc, same spirit as
BACKLOG.md — update it in place as gaps close, don't let it drift from
Hindsight (bank `hermes`), and prefer verifying live state over trusting an
older note here or in ARCHITECTURE.md.

**Sources for the "Hermes today" column:** live inspection of
`/home/hermes/.hermes/config.yaml`, `tools/`, `skills/`, `plugins/` on host
`server` (192.168.40.250) via Salt on 2026-10-31, cross-checked against
Hindsight recall. Where the two disagree, that's flagged explicitly rather
than silently picked.

## Headline finding: this isn't a from-zero build

Hermes already has most of the *mechanisms* CC relies on (subagents,
terminal execution with multiple backends, browser automation, computer
use, scheduling, a large skill library, MCP client support). The real gaps
are narrower than "Hermes can't do X" — mostly:

1. **Not wired up on this host** — e.g. only the `hindsight` MCP server is
   registered in config.yaml; `infra` (Salt), `netbox`, and Vaultwarden
   aren't, despite Hermes supporting generic MCP servers just fine.
2. **Lost in migration, not never-built** — Hindsight recall turned up
   Hermes's vision auxiliary route (`deepseek-v4.1-flash`, confirmed working
   2026-10-13) and a working Vaultwarden plugin (confirmed 2026-10-24), both
   from the old VPS/Docker install. The current native-on-`server` install's
   `plugins/` directory is empty and `vision:` is fully commented out in
   config.yaml — these look dropped during the move to `server`, not
   something that needs inventing from scratch. A 2026-10-22 "fresh start"
   incident is on record losing cron jobs, kanban/state DBs, sessions, and
   vault memories the same way — this is a pattern, not a one-off.
3. **Genuinely missing or needs hardening** — no fallback model, no
   confirmed destructive-action approval gate, no backup for Hindsight.

## Capability matrix

| Capability | Claude Code | Hermes today | Gap type | Priority |
| --- | --- | --- | --- | --- |
| Shell/terminal execution | Bash tool, persistent cwd, background procs | **Has it** — `terminal.backend` supports local/Docker/SSH/Daytona/Singularity/Modal/Vercel Sandbox; currently `local` on `server` (real host access, not sandboxed) | At parity | — |
| File edit | Read/Edit/Write, diff-based | **Has it** — file tools confirmed (BACKLOG's tilde-path bug was specific to the old Docker backend; moot now on `local`, but re-verify) | At parity, re-verify | P2 |
| Code execution (stateful) | Bash only, no persistent kernel | **Exceeds CC** — `execute_code` keeps a persistent kernel across calls in one conversation | Hermes ahead | — |
| Subagent delegation | Agent tool, Explore/Plan/general-purpose/etc., worktree/remote isolation | **Has it** — `delegate_task`, batch mode (default 3 parallel), orchestrator role, depth up to 3 | At parity | — |
| Browser automation | Two surfaces (in-app + Chrome ext.), full DOM/console/network access | **Has it** — bundled `agent-browser` + `chromium` tools | At parity, re-verify DOM/console/network parity | P2 |
| Computer use (desktop) | computer-use tools | **Has it** — bundled `cua-driver` + `computer-use` skill | At parity | — |
| Vision / screenshot understanding | Native (Sonnet 5 is multimodal) | **Regressed** — `vision:` block fully commented out in live config; historically working on `deepseek-v4.1-flash` (2026-10-13) before migration | Lost in migration | **P0** |
| Infra control (Salt) | `infra` MCP server registered | **Missing from config** — `infra_mcp.py` exists and works (proven by this CC session), just not in Hermes's `mcp_servers:` | Not wired up | **P0** |
| NetBox | `netbox` MCP server registered | **Missing from config** — same situation as infra | Not wired up | **P0** |
| Secrets (Vaultwarden) | `bitwarden` MCP server registered | **Regressed** — native plugin confirmed working 2026-10-24, `plugins/` dir on `server` is now empty | Lost in migration | **P0** |
| Scheduling / cron | CronCreate/schedule skill, ScheduleWakeup | **Has it, arguably ahead** — native `cron:` config + kanban review dispatch; add the netbox-sync-style cron work directly as a Hermes-owned job once infra MCP is wired | At parity+ | — |
| Memory | File-based auto-memory (this repo) | **Has it, arguably ahead** — Hindsight MCP (already the project's memory system) + built-in memory (disabled) + optional Honcho cross-session modeling | At parity+ | — |
| Messaging/channel presence | None (chat-session only) | **Exceeds CC** — native Telegram/Discord/WhatsApp/Slack/Signal/QQ/Teams/Google Chat platform toolsets configured in `platform_toolsets:` | Hermes ahead | — |
| Skills library (general) | ~40 bundled skills | **Has it, broader in places** — large bundled library (apple/creative/devops/email/media/productivity/research/social-media/software-development/web); includes `claude-code` and `codex` skills, i.e. Hermes can shell out to CC/Codex itself when it needs that power | At parity / escape-hatch built in | — |
| Skills library (devops/engineering meta) | schedule, loop, run, init, security-review, update-config, keybindings-help, fewer-permission-prompts | **Thin** — only `sdlc-review` under `devops/`; `software-development/` has codebase-inspection, github, debugging, TDD, code-review, simplify-code but nothing like CC's harness-config meta-skills | Partial | P1 |
| Fallback model / outage resilience | N/A (cloud frontier model, no local SPOF) | **Missing** — no fallback provider configured; single dependency on `w_workstation:8090` llama.cpp; prior crash-under-concurrency incident (needs re-verification on current version/backend) | Genuinely missing | **P0** |
| Destructive-action safety | Explicit 3-tier action classification (prohibited / needs-explicit-permission / regular), hardcoded | **Unclear/concerning** — BACKLOG recorded a flagged `rm -rf` auto-approved with zero confirmation under `GATEWAY_ALLOW_ALL_USERS=true`; no equivalent structured policy confirmed on current install | Genuinely missing / needs design | **P0** |
| Artifact/web-page publishing | Artifact tool — versioned, shareable, optional live runtime | **No direct equivalent** — closest is browser + computer-use, not a hosting primitive | Minor gap | P2 |
| Structured mid-task clarification | AskUserQuestion (typed multi-choice UI) | Chat-native (any message can ask a question); no dedicated structured-choice UI confirmed | Minor UX gap | P2 |
| Google/Office connectors (Gmail, Calendar, Drive, Notion, Slack, Docs) | OAuth connectors, live in this session | **Partial, native-flavored** — bundled skills exist (`google-workspace`, `notion`, `email`/himalaya, `docx`/`pdf`/`xlsx`/`powerpoint`) but need real credentials provisioned; not a build gap, a configuration/credentials gap | Needs provisioning | P1 |
| Backup/redundancy of Hermes's own state | N/A (stateless per-session) | **Missing** — Hindsight has no export/backup cadence (known gap, see CLAUDE.md); Hermes/Hindsight centralization raises single-point-of-failure risk | Genuinely missing | P1 |

## Priority roadmap

**P0 — do first, these are the load-bearing gaps:**
1. Wire `infra` (Salt) and `netbox` MCP servers into Hermes's
   `mcp_servers:` block on `server` — mechanically identical to what's
   already registered for Claude Code in `.mcp.json`, just needs adding to
   `/home/hermes/.hermes/config.yaml`. Lowest-effort, highest-value item
   here.
2. Restore the Vaultwarden plugin (confirmed working 2026-10-24, missing
   from the current `plugins/` dir) and the vision auxiliary route
   (confirmed working 2026-10-13 on `deepseek-v4.1-flash`, now commented
   out) — both look like migration regressions, not new builds.
3. Configure a real fallback provider for the main model — re-verify
   whether the old concurrency-crash issue (ik_llama.cpp-specific) still
   applies now that `server`'s backend is mainline llama.cpp / terminal is
   `local`, but a fallback chain is missing regardless of that.
4. Design and verify a real destructive-action approval gate — the
   zero-confirmation `rm -rf` auto-approval finding needs a closed loop, not
   just a logged-and-parked risk.

**P1 — close for daily-use confidence:**
- Provision real credentials for the Google/Office/Notion skills so they're
  usable, not just present.
- Fill in devops/engineering meta-skills (something like CC's
  `update-config`/`security-review`/`fewer-permission-prompts`) so Hermes
  can maintain its own harness config the way it's starting to maintain its
  own runtime.
- Stand up a periodic Hindsight export/backup (tracked gap in CLAUDE.md
  already — this migration history is exactly why it matters now).

**P2 — nice-to-have, revisit once P0/P1 land:**
- Re-verify the old tilde-path and terminal-backend bugs are actually moot
  under `terminal.backend: local`.
- Decide if an Artifact-equivalent (hosted, shareable page) is worth
  building, or if browser+computer-use already covers the real use cases.
- Decide if a structured clarification UI is worth building for chat
  platforms that support rich replies (Telegram/Discord do).

## Open discrepancies to resolve, not yet acted on

- **Hindsight port mismatch**: live `config.yaml` on `server` points
  Hindsight's MCP client at `192.168.40.100:8891`; this repo's own memory
  cites `:8888`. Could be two different components (raw Hindsight API vs.
  an HTTP-MCP sidecar) — confirm which before relying on either number.
- **Migration pattern risk**: this is now the *second* documented instance
  (2026-10-22 "fresh start" data loss, and the vision/Vaultwarden
  regression found here) of Hermes losing working configuration across a
  host move. Worth asking, before the next move: what's the actual
  migration checklist, and is it written down anywhere Hermes itself could
  follow it next time?
