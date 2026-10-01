# Session Seed — Post-Migration State + Resume the vLLM MoE Work

Paste this whole file as your opening message.

## What happened this session (2026-09-29/30), all verified live

**`server` (192.168.40.250) had repeated unclean crashes** (3+ boots in a row
ending in "crash" per `last -x`, no OOM/disk/NVMe/MCE root cause found, no
ECC RAM to catch a memory fault if that's the cause). Masked all systemd
sleep targets as a test/mitigation (`sleep.target`, `suspend.target`,
`hibernate.target`, `hybrid-sleep.target`) — root cause still unconfirmed,
watch for recurrence. A separate, unrelated finding: the `tailscale`
container on `server` has been crash-looping continuously since July
(dormant, never joined a tailnet) — not the crash cause, still unfixed.

**Migrated the automation/networking backbone off `server` onto
`fileserver` (192.168.40.2)**, each piece its own Docker container:
1. **Catalog** (`catalog-db`/`catalog-api`) — data verified via matching
   row counts + spot checks. All consumers repointed (this repo, shared
   `Home Claude/CLAUDE.md`, hermes-vps's `catalog_mcp.py`).
2. **Squid** — same ACL, consumers repointed (`w_workstation`'s proxy env
   vars, hermes-vps's `search_mcp.py`).
3. **WireGuard** — exact keypair preserved from `server`, so hermes-vps
   needed zero config changes (peers keyed by public key, not IP). Hit and
   fixed two issues: a knocked-out default route on fileserver (netplan
   config was fine, just needed reapplying) and a `DROP`-policy FORWARD
   chain silently blocking LAN forwarding (added explicit ACCEPT rules,
   persisted in the container's PostUp/PostDown).
4. **Salt master + API** (`cdalvaro/docker-salt-master:3008.2_3`, matches
   the exact Salt version already in use) — minion *identity* (accepted
   keys) preserved via copying `/etc/salt/pki/master/`, but **the
   container generated a brand-new master keypair on first start despite
   the mounted files** (silently overwrote the symlinks — never found the
   exact mechanism to stop this; worth investigating if redone). Fixed by
   deleting each minion's cached `minion_master.pub` and letting it
   re-trust on reconnect. All 6 minions (`fileserver`, `laptop`, `server`,
   `w_desktop`, `w_laptop`, `w_workstation`) now on the new master, old
   master/API stopped+disabled on `server`.

   **Real friction hit along the way, useful if this happens again:**
   `w_workstation`'s and `w_laptop`'s minions went fully unresponsive
   (likely a PowerShell `Set-Content` BOM/encoding issue breaking the
   minion's YAML config parse) with no remote fix possible — `w_workstation`
   has a pre-staged SSH fallback (`workstation_llm_ed25519` key, `llm@`
   user) but it was *also* unreachable (port 22 timeout, not an auth
   failure) until the user manually restarted the service via RDP.
   `w_desktop`/`w_laptop` have **no SSH/WinRM fallback at all** — pure
   RDP-only recovery. User raised this as a real pain point: Salt's
   feedback when something breaks is close to useless ("not connected",
   no why). Open thread: evaluate Netdata (shipped native MCP support Feb
   2026) for independent observability, and a WinRM-based MCP server for
   Windows execution specifically, as a more diagnosable layer alongside
   or instead of Salt's Windows minion. Not started yet.

## Open thread, paused mid-work by the server crash: local model upgrade

Before the crash was discovered, the actual goal in progress was moving
Hermes's local-tier model from `qwen3-vl:4b-hermes-instruct` (Ollama) to a
MoE model for more capability at comparable speed, decided as follows:

- **Model**: `Qwen3-VL-30B-A3B-Instruct` (31B total/3.3B active, vision
  confirmed, native Hermes tool-calling format). Quant: `QuantTrio/Qwen3-VL-30B-A3B-Instruct-AWQ`
  (~17GB, needs partial VRAM/RAM split on the 16GB A4000 — real-world
  precedent exists for this exact model size on 16GB-class cards).
- **Engine**: vLLM, not Ollama — Ollama has no MoE-aware expert-offload
  control (confirmed open unresolved upstream issue). vLLM has
  `VLLM_EXPERTS_LOAD_DEVICE=cpu` (merged) for GPU/CPU mixed expert
  placement, and native `--tool-call-parser hermes` support (Qwen3's own
  chat template already uses Hermes-style tool-call format — unrelated
  naming coincidence, not about this project).
- **Windows caveat**: vLLM has no official Windows build. Decided path:
  WSL2 + real upstream pip install (not the unofficial native Windows
  fork, not Docker Model Runner) — need the genuine latest vLLM for the
  MoE offload feature.
- **Context window**: Hermes has a hard-coded `MINIMUM_CONTEXT_LENGTH =
  64_000` floor (`agent/model_metadata.py:272` on hermes-vps) — vLLM's
  `--max-model-len` must be ≥65536, matched exactly in `config.yaml`'s
  `context_window` for the new provider entry (`discover_models: false`,
  so Hermes trusts the static config value, doesn't live-probe).
- **Ollama removal**: plan was to fully verify the new vLLM setup working
  end-to-end (including this context-window matching) while Ollama stays
  running as a fallback, only then decommission Ollama on `w_workstation`.
- **Not yet done**: installing WSL2 (if not already present) on
  `w_workstation`, installing vLLM inside it, pulling the model, wiring
  the new provider into `config.yaml`, and the actual head-to-head
  benchmark (speed + tool-call correctness) against the current 4B.

## Where the full history lives

- Full decision history: `curl "http://192.168.40.2:3003/entities?tags=cs.%7Bhermes%7D&order=created_at.desc"`
- This session's infra migration specifically: `curl "http://192.168.40.2:3003/entities?tags=cs.%7Bhermes%7D&body=ilike.*migrat*"`
- Architecture reasoning: [ARCHITECTURE.md](ARCHITECTURE.md)
- Open questions / non-goals: [BACKLOG.md](BACKLOG.md)
- Repo-specific working conventions: [CLAUDE.md](CLAUDE.md)

## Ground rules (apply automatically — do not ask permission for these)

- **Memory and git upkeep are your job.** Log decisions/facts to the
  catalog as they happen — tagged `hermes`, atomic format. Commit and push
  to `git@github.com:markstephenguy-bit/hermes.git` as work lands. Run
  `python3 scripts/export_catalog_memory.py` after catalog writes and
  commit the resulting `memory/catalog-export.json`.
- **Verify, don't trust prior notes** — this exact session caught itself
  wrong multiple times (wrong IP for a hostname, assumed-working tokens
  that had expired, an image silently regenerating keys despite mounted
  files). Check live state before acting on anything this file or the
  catalog claims, including this one.
