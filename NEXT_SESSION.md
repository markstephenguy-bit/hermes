# Session Seed — Validate & Refine the Ollama Local-Model Setup for Hermes

Paste this whole file as your opening message. This session has ONE job:
**validate that qwen3-vl:8b-hermes-instruct is actually the right local model
for Hermes, and refine the setup if it isn't.** The prior session that
produced this seed covered a lot of unrelated ground (RDP/VNC access, laptop
sleep settings, email, firewall hardening) — none of that is in scope here.
Don't re-derive it; query the catalog if you need it (see bottom).

## Current state (as of 2026-09-28, all verified live, not assumed)

- **Primary model**: `qwen3-vl:8b-hermes-instruct` on Ollama
  (`w_workstation`, 192.168.40.100:11434) — a custom tag (`num_ctx=65536`)
  built from the official `qwen3-vl:8b-instruct` release. Capabilities:
  `completion, vision, tools` — deliberately the **non-thinking** sibling of
  `qwen3-vl:8b` (which defaults to a "Thinking" build with a confirmed,
  unfixable Ollama template bug — https://github.com/ollama/ollama/issues/14798 —
  that makes `think:false` silently no-op and produced wildly inconsistent
  93s-worst-case latency). The swap to `-instruct` dropped the same
  question from 93s worst-case to 0.6-0.9s, with tool-calling and vision
  both re-verified intact.
- **Ollama service**: real NSSM-wrapped Windows Service (`OllamaService`),
  not the scheduled-task/service confusion from earlier — has actual crash
  recovery now (live-tested: killed the process, NSSM restarted it
  automatically). `OLLAMA_KEEP_ALIVE=24h` and `OLLAMA_KV_CACHE_TYPE=q8_0`
  set at Machine level. Outbound traffic (model pulls etc.) routed through
  the existing Squid proxy on `server:3128` via `HTTP_PROXY`/`HTTPS_PROXY`
  env vars, since LM Studio's inability to do this (confirmed open upstream
  bug) was the original reason Ollama was chosen over it — don't relitigate
  that choice without re-reading why.
- **Routing**: `scripts/complexity_router.py` (systemd service
  `complexity-router.service` on hermes-vps, port 11500) sits between
  Hermes and Ollama. Hermes's `model.base_url` points at the router, not
  directly at Ollama — the router is what Hermes thinks "the model" is.
  Two escalation paths, both landing on Hermes's own native
  `fallback_model` retry mechanism (openai-codex/gpt-5.6-sol) via a
  deliberate `503`:
  1. **Upfront** (`classify()`): keyword/length/code-block heuristic on the
     question, before ever calling Ollama. Crude by design — flagged by the
     user as not good enough long-term (see Open Questions).
  2. **Post-hoc** (`looks_inadequate()`): checks Ollama's actual answer for
     empty/refusal/truncated/degenerate-repetition, even when the question
     looked simple. Requires buffering full responses (loses live
     token-by-token streaming display for the local path — total latency
     unaffected, just not progressive).
- **VRAM math** (16GB RTX A4000): ~5.7GB weights + KV cache. At 64K context
  with q8_0 cache this leaves meaningfully more headroom than the earlier
  fp16-cache math (~9GB at 64K) — **not yet recalculated or acted on**, see
  Open Questions.

## Open questions this session should actually resolve

1. **Is qwen3-vl:8b-hermes-instruct the right model at all, or just the
   least-broken one we tried?** Only two candidates were ever pulled and
   tested tonight (`qwen3-vl:8b` thinking, then `-instruct`). Never
   benchmarked against `gemma4:12b` (also vision+tools+256K, tighter VRAM
   fit) or a non-vision option like `qwen3:8b`/`llama3.1:8b` paired with a
   separate small vision model only invoked when an image is actually
   present. Speed and tool-calling are verified; **actual answer quality
   on realistic queries (not just "capital of X") is not verified at all.**
2. **Now that q8_0 KV cache is live, should num_ctx go higher than 64K?**
   The 64K ceiling was chosen under fp16-cache math specifically to leave
   headroom; q8_0 roughly halves that cost. Recalculate and consider
   raising it — more context is generally better for an agent unless VRAM
   headroom actually runs out.
3. **Replace the keyword-heuristic upfront classifier with something real.**
   `routellm/bert` (HuggingFace, self-hosted, ~1.1GB, CPU-only, trained on
   real preference data, generalizes across model pairs without
   retraining) was identified as the right tool but never built. This was
   explicitly requested by the user and deferred, not abandoned.
4. **`classify()`'s word-count check sometimes sees Hermes-formatted text**
   like `"User: ... \n\nAssistant: ..."` embedded in a single message's
   content instead of clean multi-turn messages — noted as a caveat,
   never actually investigated. Could cause the >120-word threshold to
   fire on multi-turn context that isn't actually the new question.
5. **Post-hoc thresholds are untuned.** `looks_inadequate()`'s repetition
   ratio (0.3) and refusal-phrase list were picked once, not validated
   against real usage. Watch `/home/hermes/.hermes/logs/complexity_router.log`
   for false positives/negatives as this gets used more.

## Ground rules (apply automatically — do not ask permission for these)

- **Memory and git upkeep are your job.** Log decisions/facts to the
  catalog as they happen — tagged `hermes`, atomic format (one-sentence
  `body`, structured `attributes`, `relations` edges to connect related
  entities). Commit and push to
  `git@github.com:markstephenguy-bit/hermes.git` as work lands. Run
  `python3 scripts/export_catalog_memory.py` after every catalog write and
  commit the resulting `memory/catalog-export.json`.
- **Never hand-type or accept a live sudo/RDP/login password from the
  user.** For hermes-vps (SSH root@207.148.2.224) this doesn't apply — SSH
  key access is already the established pattern. For `server` and
  `w_workstation`, privileged actions go through the **Salt REST API**
  (`http://192.168.40.250:8000`, PAM eauth as `mark`, password decrypted
  from the catalog's `server-mark-sudo` secret — passphrase supplied
  in-chat, never stored) — this is a pre-established automation credential
  for exactly this purpose, not a live password grab. `w_workstation` is a
  Salt minion (`tgt: "w_workstation"`, PowerShell via
  `kwarg: {"shell": "powershell"}`).
- **Verify, don't trust prior notes** — this exact session chain caught
  itself being wrong multiple times tonight (wrong "Windows Service"
  assumption, wrong Squid-routing direction, wrong latency root cause on
  the first two guesses). Check live state before acting on anything this
  file or the catalog claims, including this file.

## Where the full history lives

This file is a snapshot, not the source of truth.
- Full decision history: `curl "http://192.168.40.250:3003/entities?tags=cs.%7Bhermes%7D&order=created_at.desc"`
- Everything from tonight's model-setup work specifically:
  `curl "http://192.168.40.250:3003/entities?tags=cs.%7Bhermes%7D&body=ilike.*ollama*"`
- Architecture reasoning: [ARCHITECTURE.md](ARCHITECTURE.md)
- Open questions / non-goals: [BACKLOG.md](BACKLOG.md)
- Repo-specific working conventions: [CLAUDE.md](CLAUDE.md)
- The router itself: [scripts/complexity_router.py](scripts/complexity_router.py)
- The catalog MCP tool Hermes can call directly: [scripts/catalog_mcp.py](scripts/catalog_mcp.py)
