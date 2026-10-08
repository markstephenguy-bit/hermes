# Session Seed — Hermes-VPS Full Reimage, Continued

Paste this whole file as your opening message.

## Where we are

The previous session ran six rounds of live capability testing against
hermes-vps (pure-local-Qwen3.6-35B-A3B profile, no Codex fallback) through
Hermes's own `/v1/responses` agent API — not raw model completions, the
actual tool-equipped agent. Found ~10 real issues (two precisely root-caused
in hermes-agent's own source, several infrastructure/policy gaps, one live
production crash caused by a concurrency test and recovered in-session).
Given the volume of findings, Mark decided: **wipe hermes-vps back to the
Vultr marketplace template and rebuild it from scratch**, applying everything
learned, rather than patch around it piecemeal.

**The full runbook for that rebuild is already written and approved:**
`/home/mark/.claude/plans/splendid-stargazing-flurry.md` — **read this file
first**, it's the actual plan (context, 8 phases, verification steps). This
seed doc is orientation + the facts that would cost real time to rediscover;
the plan file is the thing to execute.

## Immediate next action

Start at **Phase 1** of the plan (backup everything on hermes-vps before
touching anything). **Phase 2 — the actual Vultr console "Reinstall" click —
is Mark's to do, not yours**: no account-level Vultr API key exists anywhere
in the vault (only a Serverless Inference key), confirmed in the previous
session. Do Phase 1, then stop and wait for Mark to confirm he's done the
reinstall in the Vultr console before starting Phase 3.

## Ground rules already established this project (don't relitigate)

- Setup/config on hermes-vps happens BY Hermes itself (its own CLI/chat) where
  practical, not by editing files directly where avoidable — Claude Code
  orchestrates and verifies. (The reimage plan is an explicit, Mark-approved
  exception: rebuilding the box itself obviously can't go through Hermes's
  own chat, since Hermes doesn't exist yet on a freshly wiped box.)
- Memory and git upkeep are Claude's job, not the user's — log to the catalog
  (tag `hermes`) and commit/push as work lands, don't batch silently.
- Source of truth: `Hermes_Way.xlsx` (tracked backlog) for the broader
  project; `BACKLOG.md` in this repo for the current reimage-era punch list;
  the catalog has full decision history — query it, don't trust cached
  assumptions.
- **One-hop rule**: if executing a step surfaces something broken that isn't
  itself part of the current step, diagnose to root cause, then stop and
  report before fixing — don't chain fix after fix without checking in.
- **Never self-report success without independent verification.** Always
  confirm on disk / via an independent check, not the agent's own narration —
  Hermes's own chat sessions have hallucinated "wrote the file" when nothing
  was written.
- Batch work — do a full chunk via tool calls before producing chat text.
  Don't narrate every poll tick or intermediate step.
- Take simple instructions directly — don't interject with nuance, caveats,
  or clarifying questions for things that are actually simple. Ask only when
  something is genuinely ambiguous or requires info only the user has.

## Critical facts from the testing session (would cost real time to rediscover)

- **Testing method**: SSH local port-forward to hermes-vps's port 8642
  (`ssh -L 18642:127.0.0.1:8642 root@207.148.2.224`), then POST to
  `/v1/responses` with `Authorization: Bearer <API_SERVER_KEY>`. Avoids
  per-call SSH+CLI cold-start. A dedicated `hermes-testing` profile
  (multiplexed on the same gateway, its own API key, fresh SOUL/USER/MEMORY)
  keeps test artifacts from touching the real default profile's memory — see
  catalog entity `hermes-testing-profile-created-2026-10-07` for exactly how
  it was built; it will need recreating after the reimage.
- **Reusable test battery**: `testing/stress_test_1.py` through `_4.py` in
  this repo (see `testing/README.md`) — re-run these post-rebuild to confirm
  nothing regressed and the two patched bugs (below) now pass. **Caution**:
  `stress_test_4.py`'s concurrency/fan-out tests are what crashed the model
  server last time — read the warning in that file before running it again.
- **Tilde-path bug** (P0, root-caused): `write_file`/`patch` resolve `~` via
  a static host-process home concept (`hermes_constants.get_subprocess_home()`
  branching on `is_container()`, which checks the *agent process's* own
  containment, not the *terminal backend's*); `read_file`/`terminal` resolve
  it via a live in-container `echo $HOME`. Disagree whenever the host
  process's home differs from the container's — i.e. always, on this
  deployment. Full detail + exact file/function names:
  catalog entity `hermes-tilde-bug-is-container-mismatch-2026-10-07`, and
  Phase 6 of the plan.
- **`/v1/skills` bug** (root-caused): `gateway/platforms/api_server.py`
  calls `_find_all_skills(include_editorial=True)`, but `tools/skills_tool.py`
  only accepts `skip_disabled` — 100% reproducible `TypeError`, zero load
  needed. Catalog entity `hermes-v1-skills-endpoint-broken-2026-10-07`.
- **The concurrency ceiling is real and low**: the ik_llama.cpp server has
  exactly ONE inference slot. ~10 simultaneous requests (an 8-way subagent
  fan-out plus 2 concurrent same-session calls) crashed it outright
  (`STATUS_STACK_BUFFER_OVERRUN` per Windows Task Scheduler). No fallback
  provider exists (Codex was intentionally removed for pure-local-Qwen mode),
  so a crash currently means ALL of Hermes is down with no automatic
  recovery. Mark has decided a fallback provider must be added, **but
  explicitly after** the current issue-finding/rebuild phase, **and** it
  must include its own rate limit/circuit breaker on the fallback path — the
  same retry-storm mechanism that crashed the local model for free would, hitting
  a paid API instead, turn into an unexpected bill. Catalog entities
  `hermes-concurrency-induced-llama-server-hang-2026-10-07`,
  `hermes-llama-server-crash-resolved-2026-10-07`,
  `hermes-fallback-needs-circuit-breaker-2026-10-07`.
- **`hermes backup` / `hermes import`** is the vendor's own documented
  "move to another machine" mechanism — covers `config.yaml`, `state.db`,
  `.env`, `auth.json` (the Nous Research / ChatGPT Plus OAuth login — the one
  piece of state that's genuinely painful to redo), cron jobs, memories,
  sessions, skills. This is what de-risks the whole reimage; see Phase 1/3 of
  the plan for exact usage.
- **Vultr Auto Backups are enabled** on hermes-vps (full-disk snapshots,
  infrastructure level) — an independent safety net regardless of anything
  the plan does.
- **WireGuard keys are deliberately host-local**, never vaulted — a fresh
  install generates a new keypair, requiring re-pairing with the home
  `server` node's peer config (see catalog entity
  `server-wireguard-configured-2026-09-25` for the exact pattern, and Phase 3
  of the plan).
- **A real, unrelated issue found and bundled into this rebuild**:
  `scripts/salt_client.py` line 12 has a vault decryption passcode hardcoded
  in plaintext, already pushed to git. Fix per "Finding 0" in the plan:
  remove the hardcode (env/prompt instead), rotate the actual passcode.
- **`scripts/complexity_router.py` in this repo has already diverged** from
  what's actually deployed on hermes-vps (repo copy is an older Ollama/Codex-
  judge design; live version was rewritten for the ik_llama.cpp + Vultr-vision
  split). Don't redeploy the repo copy blindly during the rebuild — Phase 4 of
  the plan explains how to reconstruct the current version instead.

## Full list of catalog entities from the testing session (tag `hermes`)

Query `curl "http://192.168.40.2:3003/entities?tags=cs.%7Bhermes%7D&order=created_at.desc&limit=40"`
for the complete, current list with full detail — the bullets above are the
highlights, not the whole picture. `hermes-integration-priority-list-2026-10-07`
is the consolidated, prioritized punch-list that synthesizes all of it.
