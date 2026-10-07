# Session Seed — Hermes Way Execution, Continued

Paste this whole file as your opening message.

## Ground rules already established this project (don't relitigate)

- Setup/config on hermes-vps happens BY Hermes itself (its own CLI/chat), not by editing files directly where avoidable. Claude Code orchestrates and verifies.
- Memory and git upkeep are Claude's job, not the user's — log to the catalog (tag `hermes`) and commit/push as work lands, don't batch silently.
- Source of truth: `Hermes_Way.xlsx` (tabs 01-15 tracked backlog, D1-D8 discovery/reference only, no points). The catalog has full decision history. Query the catalog, don't trust cached assumptions.
- **General identity files (SOUL.md, memories/USER.md, memories/MEMORY.md) are about Hermes in general, never project-specific.** Project-specific facts belong in their own `hermes project create <name> <folder>`, with their own files.

## Behavioral workflow the user wants (established hard, after real friction)

1. Every chunk of work starts by naming a row: `Row: <ID> (<pts>pts, <tab>) — target: <what done looks like>`.
2. **One-hop rule**: if executing a row surfaces something broken that isn't itself a row, diagnose to root cause, then stop and report before fixing — don't chain fix after fix without checking in.
3. **Host-boundary check**: if a row's "Must Live On" is Hermes-VPS but the work is about to touch a different host, that's a stop-and-ask.
4. Every response ends with: `Row: <ID> | Status: <unchanged/partial/done> | Next: <single action>`.
5. **Take simple instructions directly — do not interject with nuance, caveats, or clarifying questions for things that are actually simple.** Execute, then report. Ask only when something is genuinely ambiguous or requires info only the user has.
6. **Never self-report success without independent verification.** Hermes's own chat sessions have hallucinated "wrote the file" when nothing was written — always confirm on disk / via an independent check, not the agent's own narration.
7. Batch work — do a full chunk via tool calls before producing chat text. Don't narrate every poll tick or intermediate step.

## Critical non-obvious facts discovered this session (would cost real time to rediscover)

- **`terminal.docker_mount_cwd_to_workspace` must be `true`** (config.yaml, default `false`). Without it, every file Hermes writes via its sandboxed terminal/file tools vanishes when the ephemeral sandbox container exits — zero host persistence. Already fixed and set to `true` on hermes-vps. If this is ever a fresh install, set it immediately.
- **SOUL.md lives at `~/.hermes/SOUL.md` (top-level)**. **USER.md and MEMORY.md live at `~/.hermes/memories/USER.md` and `~/.hermes/memories/MEMORY.md`** — NOT top-level. They are agent-grown stores populated through real use, not static docs to hand-author. `memories/USER.md` already has real pre-existing content from genuine prior Hermes usage (predates this whole project thread) — never overwrite it blindly.
- **`HERMES_DISABLE_LAZY_INSTALLS=1`** is set in `.env` — blocks Hermes's own auto-install of optional deps (e.g. `python-telegram-bot`). To install manually: the runtime venv has **no pip**, use `uv pip install --python <venv>/bin/python <package>`. Runtime venv path: `/home/hermes/.hermes/installs/019d0d114d22b7e6/environments/b6f36e8a90d54eddb9e48660acb56fbb/venv` (may change on upgrade — find via `hermes doctor`'s "Runtime venv staged" line).
- **`hermes-gateway.service` is a persistent SYSTEM-level systemd unit** (survives reboot, verified via an actual reboot test). Any `.env`/config change affecting the gateway needs `systemctl restart hermes-gateway` — it won't pick up changes on its own. Don't run `hermes gateway install` casually — it creates a separate USER-level service alongside the system one, causing duplicate/ambiguous gateways (had to uninstall one tonight).
- **`complexity-router.service`** (systemd, port 11500, source `/home/hermes/.hermes/complexity_router/complexity_router.py`) is a custom LLM-as-judge proxy: routes between local Ollama (`OLLAMA_BASE_URL=http://192.168.40.100:11434`, i.e. w_workstation) and Codex fallback. `model.provider=ollama` + `base_url=http://127.0.0.1:11500/v1` in config.yaml points here, not at real Ollama directly.
- **Local model reality**: Ollama is live and working RIGHT NOW on w_workstation (RTX A4000), serving `qwen3-vl:4b/8b-hermes-instruct` variants — this is the ACTIVE provider. Separately, `ik_llama.cpp` was built from source on w_workstation (CUDA, sm_86) at `C:\ik_llama.cpp\build\bin\llama-server.exe` as the planned upgrade (LI-03/04 target: Qwen3.6-35B-A3B) — built but **not yet pulled a model, not yet wired into the router, not yet benchmarked**. Don't assume ik_llama.cpp is in use — Ollama is.
- **Salt master is at `fileserver` (192.168.40.2:8000)**, not `server` (192.168.40.250) — a stale catalog note said otherwise, corrected. Salt eauth: scoped user `hermes-infra` (perms: cmd/disk/network/service/status/test only), credential in vault as `salt-hermes-infra`. Login: `POST /login` with `eauth=pam`.
- **w_workstation SSH** (192.168.40.100, user `llm`, key `~/.ssh/workstation_llm_ed25519`) had a broken `sshd` service (capability showed Installed but service was never registered) — fixed by removing+re-adding the `OpenSSH.Server` Windows capability via Salt, then starting/enabling `sshd`+`ssh-agent`. If it breaks again, that's the fix.
- **Dokploy** was never set up (zero users) despite being installed. Signup completed: `mark.stephen.guy@gmail.com` (vault: `hermes-vps-dashboard-basic-auth`... actually vault key is `hermes-vps-dokploy-admin` — **password reuses the vault master passcode, recommend rotating**). Its API is tRPC at `/api/trpc/<procedure>` — e.g. `project.create`, `application.create`, `application.saveDockerProvider`, `application.deploy`.
- **Windows build toolchain on w_workstation**: the pre-existing VS2022 Community install only has the OneCore/UWP library variant (no `msvcrt.lib`), not usable for normal desktop builds. A fresh, independent Build Tools install was done at `C:\BuildTools2022` with the full desktop C++ workload — use that one for any future native builds, not the pre-existing Community install. Standalone CMake at `C:\Program Files\CMake`, standalone Ninja at `C:\ninja`, CUDA Toolkit 12.6.3 (+ cuBLAS dev libs, installed separately) at the default path.
- **SSH/PowerShell quoting over the Salt/SSH bridge is fragile** — prefer writing scripts to disk via base64 round-trip (`[IO.File]::WriteAllText(path, [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('...')))`) over inline quoted PowerShell one-liners with pipes.
- **Salt `cmd.run` has no reliable long-running/background primitive** — `Start-Job` is scoped to the invoking process (dies when the Salt call returns), and Salt itself may kill long calls on its own timeout. For long Windows operations, use `Start-Process ... -RedirectStandardOutput/-RedirectStandardError` to a log file (fully detached OS process), then poll the log file separately.

## Credentials vaulted this session (passcode: ask the user, don't assume it's still `463453551` — that's also reused as the Dokploy password, flagged for rotation)

- `hermes-vps-ssh` — root@207.148.2.224, same key as default `~/.ssh/id_ed25519`
- `hermes-vps-telegram-bot-token` — bot `@hermesagent_mark_bot`
- `hermes-vps-dokploy-admin` — mark.stephen.guy@gmail.com

## Current state vs the workbook (verify fresh — this will have moved)

**01_Core_Runtime**: 16/18 Done. Only CR-15/CR-16 open, and those are **explicitly deferred per the user** (sister's Hermes — separate project, don't touch until this Hermes instance is complete).

**02_Identity_Memory**: IM-01/02/03/06/08/09-status Done (note IM-09 itself is correctly Not Started — MEMORY.md populates through use). IM-04 (cross-interface continuity) just got unblocked by IA-05 landing — all three interfaces (CLI, Dashboard, Telegram) now exist, this is now actually testable. IM-05/IM-07 correctly Partial, blocked on SV-15 (vault/catalog migration decision) — don't force.

**08_Interfaces_Access, IA-05**: Done. Telegram gateway live, real two-way exchange confirmed.

**12_Security_Hardening**: SH-04/06/07 done this session (found and fixed a real plaintext-credential exposure in the infra MCP server's config; confirmed dashboard auth is properly hashed; ran `hermes security audit` for the first time — 68 CVE findings, mostly fixable dependency bumps, NOT yet remediated).

**07_Local_Inference**: 75% (was 26%). LI-01/02/03/04/06/07 all Done this session — ik_llama.cpp built+verified, Qwen3.6-35B-A3B pulled, context_length fixed, benchmark run. See "Local-inference benchmark results" below before touching LI-08. LI-05 (WSL2) is moot — vLLM was rejected, so this row has no remaining purpose. LI-09 (vision parity) still open.

**Everything else** (05_Secrets_Vault 17%, 09_Observability 4%, 11_Cost_Subscriptions 22%, 13_Governance_Change_Mgmt 0%, 14_Claude_Code_Parity 13%, 15_Productivity_And_Acceptance 0%) — largely untouched. Governance and Productivity/Acceptance are at zero, nothing has touched either domain yet.

## Local-inference benchmark results (this session, see catalog `hermes-li07-benchmark-results-2026-10-06`)

- ik_llama.cpp's `llama-server.exe` needs the CUDA Toolkit `bin` dir prepended to `PATH` or it fails silently (retcode 1, zero output, no error) — non-obvious, cost real time to diagnose.
- `--jinja` IS supported by this fork (was flagged unverified) — tool-calling confirmed correct (`finish_reason: tool_calls`, clean args) on Qwen3.6-35B-A3B, matching the Ollama 4B/8B baseline.
- Decode speed is comparable across all three: ~17-19 tok/s for the 35B-A3B MoE model (`--cpu-moe`, most weights offloaded to system RAM) vs ~16-19 tok/s for Ollama's 4B/8B dense models fully on GPU. Validates the MoE+CPU-offload bet behind choosing ik_llama.cpp over vLLM.
- **Blocking gotcha for production cutover**: default thinking mode is dangerously verbose — a simple 150-word-explanation prompt burned a full 1500-token budget on hidden `reasoning_content` and produced **zero** actual output (`finish_reason: length`). Must pass `chat_template_kwargs: {enable_thinking: false}` on every request; verified this produces clean, complete, correctly-terminated output at matching speed. The Ollama baseline doesn't have this problem (no reasoning_content by default).
- Test server (port 8090 on w_workstation) is a manual benchmark instance only — **not wired into complexity-router**, Ollama is still the live production provider. Wiring it in means baking the `enable_thinking: false` override into the router's request path first.
- Confirmed via Salt: no vLLM anywhere on either host (never actually installed, only evaluated/rejected) — nothing to uninstall there. Ollama stays installed; LI-08 decommission is only valid after the new provider is actually wired in and verified live, not before.

## Good candidates for next session, in rough priority order

1. **IM-04**: actually test cross-interface continuity now that Telegram exists.
2. **Wire Qwen3.6-35B-A3B into complexity-router** (supplementing, not yet replacing, Ollama) — the benchmark passed, but this needs explicit go-ahead since it changes live production routing. Must enforce `enable_thinking: false` in the request path (see gotcha above) or responses will silently fail. Only after this is verified live does LI-08 (Ollama decommission) become valid.
3. **SH-07 remediation**: bump PyJWT/httpx2/urllib3/oauthlib per the security audit findings (separate from the broader `hermes update`, which is 2547 commits behind and its own decision under CR-11's policy).
4. **MR-05** (15pts, finish-line condition #2): the WireGuard-down fire drill — never attempted. Pull the tunnel mid-conversation, confirm Hermes still answers via Codex automatically.
5. Pick up a new domain wholesale (05_Secrets_Vault or 09_Observability are both large and almost entirely untouched).

## Deliberately out of scope until further notice

- CR-15/CR-16 (sister's Hermes) — explicit user deferral.
- IA-08 (voice interface) — explicit user deferral, noted earlier in the project.
- Rotating the Dokploy password / vault passcode reuse — flagged, not acted on, user's call.
