# Qwen & DeepSeek local tool-calling candidates — 64K native-context gate

Hard requirement under test: Hermes Agent rejects any local model that cannot serve
**≥64,000 tokens of real context**. Methodology follows the order mandated by the
assignment: (1) native context first, from primary sources where possible, treating
`max_position_embeddings` in `config.json` as a *claim*, not proof — (2) VRAM/quant fit
only for context-gate survivors — (3) tool-calling benchmarks — (4) llama.cpp support
status. All `config.json` fields below were fetched live from Hugging Face
(`https://huggingface.co/<repo>/raw/main/config.json`) on 2026-10-11 unless noted.

---

## Section A — Native context verification (every candidate, including eliminations)

### Qwen2.5 family (dense, non-"-1M")

| Model | max_position_embeddings | rope_scaling | Native context verdict |
|---|---|---|---|
| Qwen2.5-0.5B/1.5B/3B/7B/14B/32B/72B-Instruct | 32768 | null | **32768, confirmed.** Config value matches Qwen2.5 model card's stated training length exactly (no buffer padding, no scaling). |
| Qwen2.5-Coder-32B-Instruct | 32768 | null | Same as above — 32768. |

**ELIMINATED — all Qwen2.5 base/Coder dense models fail the 64K gate.** Confidence: confirmed.

### Qwen2.5-1M variants (7B-1M, 14B-1M)

- `config.json`: `max_position_embeddings: 1010000`, `rope_scaling: null`, `rope_theta: 10000000` (vs 1,000,000 for standard Qwen2.5).
- **This 1,010,000 figure is itself a trap pattern** (config overstates real native length, same shape as the Qwen3-14B mistake) — but in this case the real number still clears the gate. Per the official Qwen2.5-1M blog (primary source, fetched directly): *"The final instruction-tuned models are capable of handling sequences up to 256K tokens"* — i.e., native/pretrained context is **256K tokens**, reached via progressive length-extension training. Dual Chunk Attention (DCA) and MInference sparse attention are layered on top **only to extrapolate beyond the trained 256K range, up to 1M** — the blog's own ablation shows "even models trained on just 32K tokens can achieve near-perfect accuracy at 1M tokens when DCA is applied," explicitly framing DCA as an *extrapolation* technique, not a requirement within the trained range.
- Source: [Qwen2.5-1M blog](https://qwenlm.github.io/blog/qwen2.5-1m/) (primary), [Qwen2.5-1M Technical Report](https://arxiv.org/abs/2501.15383).
- **Verdict: PASSES the 64K gate** at 256K confirmed native context, **without needing DCA/sparse-attention support at all** (64K « 256K trained range). Confidence: confirmed from primary source for the 256K number; the 1,010,000 config figure should NOT be quoted as "native."

### Qwen3 family (dense: 0.6B/1.7B/4B/8B/14B/32B; MoE: 30B-A3B, 235B-A22B)

All eight checked return **identical** values: `max_position_embeddings: 40960`, `rope_scaling: null`, `rope_theta: 1000000`.

- This matches the exact trap the previous attempt already fell into with Qwen3-14B. The Qwen3 model card convention is `40960 = 32768 (real native) + 8192 (reserved generation/output buffer)` — i.e., 40960 is *not* an extended-context number, it's native-plus-buffer, and `rope_scaling: null` confirms no YaRN is even active by default (Qwen3's own docs describe YaRN as something you must manually enable in config to reach 131072, and it is not enabled in the stock configs shipped for any dense/MoE Qwen3 size checked).
- **ELIMINATED — entire Qwen3 line (0.6B through 235B-A22B) fails the 64K gate at its real native length of 32768.** Confidence: confirmed (same evidence class as the already-validated Qwen3-14B case).

### Qwen3-Next-80B-A3B (hybrid linear/full attention MoE)

- `config.json`: `max_position_embeddings: 262144`, `rope_scaling: null`, `rope_theta: 10000000`, 48 layers, hybrid Gated-DeltaNet (linear attention) + periodic full attention.
- Primary-adjacent source (Qwen3-Next blog, via search synthesis): natively trained on 15T tokens then "extended to support context length beyond typical pretraining settings to 262,144 tokens," with instruct-model long-context performance "close to the much larger Qwen3-235B flagship ... particularly excelling ... up to 256K." This reads as genuine continued-pretraining extension, not a pure inference-time RoPE trick (no `rope_scaling` block is even present).
- **Verdict: PASSES the 64K gate** at 262144. Confidence: inferred/high — based on a vendor blog description relayed through search rather than a directly-fetched primary PDF; treat as "inferred, not fully confirmed from a quoted primary passage."
- **However — see Section B: eliminated on VRAM grounds** (80B total params, Q4_K_M GGUF alone is 48.7GB).

### Qwen3.5 family (0.8B, 2B, 4B, 9B dense; 27B dense; 35B-A3B, 122B-A10B, 397B-A17B MoE)

Released Feb–Mar 2026. Uses a new hybrid architecture (`model_type: qwen3_5` / `qwen3_5_moe`) interleaving Gated-DeltaNet linear-attention layers with full-attention layers (~75%/25% split, pattern `3×(linear→MoE) → 1×(full-attn→MoE)` repeated).

| Model | max_position_embeddings (text_config) | rope_scaling |
|---|---|---|
| Qwen3.5-0.8B / 2B / 4B / 9B | 262144 | null |
| Qwen3.5-27B | 262144 | null |
| Qwen3.5-35B-A3B | 262144 | null |

- Independent secondary coverage (trilogyai Substack deep-dive, morphllm) states: *"Qwen3.5's context length jumps to 262K natively across the full model lineup, including the 0.8B, 2B, 4B, and 9B variants ... extensible up to 1,010,000 tokens."* No `rope_scaling` block is present at the trained 262144 length, consistent with this being a genuinely trained window rather than an inference hack.
- **Verdict: PASSES the 64K gate** at 262144 for every size. Confidence: inferred — sourced from two independent secondary analyses, not a directly quoted line from Qwen's own Qwen3.5 technical report PDF (search could not retrieve the primary PDF text; only a ResearchGate page for the separate Qwen3.5-**Omni** report surfaced, which is a different, multimodal document).

### Qwen3.6 family (27B dense, 35B-A3B MoE)

Released Apr 2026 (per OpenRouter/Constellation Research coverage), same `qwen3_5` architecture family.

| Model | max_position_embeddings | rope_scaling |
|---|---|---|
| Qwen3.6-27B | 262144 | null |
| Qwen3.6-35B-A3B | 262144 | null |

- **Verdict: PASSES the 64K gate** at 262144, by direct config inheritance from the Qwen3.5 architecture family and no contradicting source found. Confidence: inferred (no dedicated Qwen3.6 technical report located; relying on architectural continuity with Qwen3.5 plus the fetched config).
- **27B and 35B-A3B both eliminated on VRAM grounds — see Section B.**

### Qwen3.8 (named in GitHub org `QwenLM/Qwen3.8`, plus `Qwen3.8-Flash-Next`)

- Found only as a GitHub repo name and an HF model id (`Qwen/Qwen3.8-Flash-Next`) surfaced via search; no config.json was fetched (out of budget) and no technical report or model card detail was retrieved beyond the name. **Not evaluated — logged as a gap**, not as a pass or fail. It appears to be a "Next"-style hybrid variant analogous to Qwen3-Coder-Next, but this is a guess, not a confirmed fact, and is explicitly flagged as such rather than stated.

---

### DeepSeek-R1-Distill family

| Model | Base checkpoint | max_position_embeddings | rope_scaling | Base's own real native |
|---|---|---|---|---|
| DeepSeek-R1-Distill-Qwen-1.5B | Qwen2.5-**Math**-1.5B | 131072 | null | Qwen2.5-Math-1.5B config: **4096** (confirmed, fetched) |
| DeepSeek-R1-Distill-Qwen-7B | Qwen2.5-Math-7B | 131072 | null | Qwen2.5-Math-7B config: **4096** (confirmed, fetched) |
| DeepSeek-R1-Distill-Qwen-14B | Qwen2.5-14B | 131072 | null | Qwen2.5-14B config: **32768** (confirmed, fetched) |
| DeepSeek-R1-Distill-Qwen-32B | Qwen2.5-32B | 131072 | null | Qwen2.5-32B config: **32768** (confirmed, fetched) |
| DeepSeek-R1-Distill-Llama-8B | Llama-3.1-8B | 131072 | `{rope_type: llama3, factor: 8.0, original_max_position_embeddings: 8192}` | Llama-3.1-8B: continued-pretrained to 128K by Meta (documented, baked-in llama3 rope scaling, not an inference-only trick) |
| DeepSeek-R1-Distill-Llama-70B | Llama-3.1-70B | 131072 | same llama3 scaling | Same — Llama-3.1-70B genuinely continued-pretrained to 128K |

**This is the single most important finding of this research, and it directly reproduces the failure pattern the assignment warned about:**

- For the **1.5B and 7B Qwen variants**, the base model (Qwen2.5-**Math**) has a real native context of only **4096 tokens**. The distilled checkpoint's config claims 131072 — a 32x jump — with `rope_scaling: null`, i.e. no documented mechanism for the extension at all. **Treat 131072 here as almost certainly false. ELIMINATED, confidence: confirmed-suspicious** (the discrepancy itself is confirmed from fetched configs; what the *true* usable length is was not independently measured, but 4096 is a hard floor and 131072 cannot be taken at face value).
- For the **14B and 32B Qwen variants**, base Qwen2.5-14B/32B native is 32768 (same number independently confirmed for the plain Qwen2.5-Instruct releases above). The distilled checkpoint again claims 131072 with `rope_scaling: null` — no YaRN, no DCA, nothing. I went to the primary source to resolve this: **the DeepSeek-R1 paper itself (arXiv 2501.12948) contains no statement about the context length used during the Qwen distillation SFT stage.** The "32,768" figure that several secondary summaries attribute to "distillation training" is, on direct inspection of the paper, actually a *generation-length cap applied during benchmark evaluation* ("DeepSeek-R1 outputs are capped at a maximum of 32,768 tokens for each benchmark") — an unrelated eval-time setting, not a training-context statement. So: the commonly repeated "32768 is the real distillation context" claim is **not substantiated by the primary paper** — but neither is the config's 131072 claim substantiated by any mechanism (no rope_scaling block exists to explain how a 32768-native base would reach 131072). **This is a genuine unresolved contradiction, not a confirmed pass or fail.** Flagging per instructions rather than silently picking a side.
  - Commercial inference providers (Groq, SiliconFlow, Novita/Requesty) uniformly list "128K"/"131K" context for these models — but this is exactly the failure mode already demonstrated with Qwen3-14B: providers and tooling frequently just mirror `config.json` without independently verifying real capability.
  - **Recommendation for whoever acts on this shortlist: do NOT treat DeepSeek-R1-Distill-Qwen-14B/32B as a confirmed pass on the 64K gate without running an explicit needle-in-a-haystack or long-context degradation test first.** Provisionally excluded from the "confirmed" shortlist below; listed separately as "unresolved — needs empirical verification."
- For the **Llama-8B/70B variants**, the extension mechanism *is* documented and architecturally legitimate: Meta's Llama-3.1 base models were genuinely continued-pretrained to 128K using the `llama3` RoPE scaling type (`original_max_position_embeddings: 8192`, `factor: 8.0`) — this is baked into the base checkpoint's own training, not something DeepSeek bolted on, and llama.cpp has native, mature support for `llama3`-type rope scaling (in place since Llama 3.1 launch in 2024). **Verdict: PASSES the 64K gate, confidence: confirmed** (architecture-level evidence, consistent with Meta's own Llama 3.1 context-extension claims). The caveat is that the R1-distillation fine-tuning data itself may not have included many long-context reasoning traces — this affects *quality* of long-context tool use, not the hard context-length gate itself, so it's noted but doesn't change the pass/fail call.

### DeepSeek-R1-0528-Qwen3-8B (newer May-2026 distill, Qwen3-8B base)

- `config.json`: `max_position_embeddings: 131072`, **`rope_scaling: {rope_type: yarn, factor: 4.0, original_max_position_embeddings: 32768, attn_factor: 0.878}`**, base Qwen3-8B real native 32768 (per Section A above).
- Unlike the Qwen2.5-based distills, this one is architecturally honest: it explicitly documents YaRN scaling in its own config, with `original_max_position_embeddings: 32768` matching Qwen3-8B's real confirmed native length, and a 4x YaRN factor reaching 131072. This is a **baked-in, self-describing** extension (not a bare unexplained number) — YaRN is a well-understood, llama.cpp-supported RoPE scaling method.
- **Verdict: PASSES the 64K gate** at 131072 via documented YaRN. Confidence: confirmed (the config is internally consistent and matches the known-good Qwen3-8B native number).

### DeepSeek-V3 / V3.x family

- No small/local-friendly checkpoints exist in this line — every DeepSeek-V3/V3.1/V3.2/R1 (non-distill) release is a ~671B-parameter MoE (~37B active). **Eliminated on practicality grounds before even reaching the context check** — none of these can be loaded on a 16GB-VRAM RTX A4000 at any quantization. Confidence: confirmed (no smaller official V3-line checkpoint was found in any search).

### DeepSeek-V2-Lite (included for completeness — older/smaller MoE, 16B total/2.4B active)

- `config.json`: `max_position_embeddings: 163840`, `rope_scaling: {type: yarn, factor: 40, original_max_position_embeddings: 4096}`.
- A **40x** YaRN stretch from a tiny 4096 native base is far more aggressive than any other candidate here and well outside the regime YaRN is normally validated for. **ELIMINATED — treat the 163840 claim as not credible; real effective usable length is almost certainly far below 64K.** Confidence: confirmed-suspicious (config fetched directly; the extreme factor is itself the red flag, consistent with how aggressive YaRN stretches degrade quality well before the nominal cap).

---

## Section B — VRAM fit (RTX A4000, 16GB) for context-gate survivors only

GGUF sizes fetched directly from bartowski's HF repos (`Q4_K_M`/`Q5_K_M`/`Q6_K`, byte-exact from the HF tree API). KV-cache estimates computed from `num_hidden_layers` (L), `num_key_value_heads` (H), `head_dim` (D) at 65536 tokens (64K), formula `bytes = 2(K&V) × L × H × D × T × bytes_per_elem`. For hybrid (Qwen3.5/3.6-style) architectures, only the ~25% full-attention layers carry a growing KV cache; linear-attention layers hold a small fixed-size recurrent state that does not scale with T — this is a major structural advantage for long-context VRAM budgets, but I could not confirm whether llama.cpp's Qwen3.5 implementation actually exploits this (vs. naively allocating full cache for all layers); flagged as a gap.

| Model | Q4_K_M size | Q5_K_M | Q6_K | Dense KV@64K (fp16 / Q8 / Q4) | Fits 16GB? |
|---|---|---|---|---|---|
| Qwen2.5-14B-Instruct-1M | 8.99 GB | 10.51 GB | 12.12 GB | ~12.9 GB / ~6.4 GB / ~3.2 GB | **Only with Q8 or Q4 quantized KV cache** (8.99+6.4=15.4GB, tight; 8.99+3.2=12.2GB, comfortable). Default fp16 KV cache (8.99+12.9=21.9GB) does **not** fit. |
| DeepSeek-R1-0528-Qwen3-8B | 5.03 GB | 5.85 GB | 6.73 GB | ~9.0 GB / ~4.5 GB / ~2.25 GB | **Fits comfortably** at Q4_K_M+Q8 KV (5.03+4.5≈9.5GB) or even Q4_K_M+fp16 KV (5.03+9.0≈14GB). |
| Qwen3.5-9B | 6.17 GB | 7.11 GB | 7.96 GB | Full-attn-only KV@64K ≈ 2.15 GB (fp16), est. (8 of 32 layers are full-attention; linear-attn layers' recurrent state is small and roughly constant, not separately sized here) | **Fits easily**, with the most VRAM headroom of any confirmed-pass candidate — structural advantage of the hybrid architecture. |
| Qwen2.5-7B-Instruct-1M | not fetched (smaller than 14B variant; expected ~4.5-5GB at Q4_K_M) | — | — | ~half of the 14B dense KV estimate (fewer layers/heads) | Expected to fit comfortably; **not independently verified — gap**. |
| DeepSeek-R1-Distill-Llama-8B | not fetched | — | — | Dense Llama-8B architecture, similar order to Qwen3-8B | Expected to fit; **not independently verified — gap**. |
| Qwen3.6-27B / Qwen3.5-27B | 17.98 GB | 20.97 GB | 23.68 GB | n/a | **Does not fit — weights alone exceed 16GB even at Q4_K_M.** ELIMINATED on VRAM. |
| Qwen3.5-35B-A3B / Qwen3.6-35B-A3B | 22.29 GB | 25.91 GB | 30.95 GB | n/a | **Does not fit** (MoE total-weight size, not active-param size, is what must be resident). ELIMINATED on VRAM. |
| Qwen3-Next-80B-A3B-Instruct | 48.73 GB | n/a (0-byte placeholder in repo) | n/a | n/a | **Does not fit by a wide margin.** ELIMINATED on VRAM. |
| DeepSeek-R1-Distill-Qwen-14B/32B | not computed (status unresolved per Section A) | — | — | — | Not evaluated for VRAM — context-gate status unresolved, so this step is withheld pending that verification. |

Sources: bartowski GGUF repos via HF tree API (`bartowski/Qwen_Qwen3-8B-GGUF`, `bartowski/Qwen_Qwen3.5-9B-GGUF`, `bartowski/Qwen2.5-14B-Instruct-1M-GGUF`, `bartowski/deepseek-ai_DeepSeek-R1-0528-Qwen3-8B-GGUF`, `bartowski/Qwen_Qwen3.5-27B-GGUF`, `bartowski/Qwen_Qwen3.6-27B-GGUF`, `bartowski/Qwen_Qwen3-30B-A3B-GGUF`, `bartowski/Qwen_Qwen3-Next-80B-A3B-Instruct-GGUF`, `bartowski/Qwen_Qwen3.6-35B-A3B-GGUF`, `bartowski/Qwen_Qwen3.5-35B-A3B-GGUF`), all fetched 2026-10-11.

---

## Section C — Tool-calling / function-calling benchmarks

### Takeaway
Current (2026) BFCL numbers are fragmented across v3 and v4 versions with no single source giving v4 scores for every surviving candidate; where only v3 was found, that is stated explicitly rather than presented as current.

### Cited findings
- BFCL v4 overall leaderboard (Sept 2026 snapshot): leader BTL-3 at 88.5%, Qwen3.6 Max (proprietary, not a local candidate) at 75.0%. Qwen "owns approximately 10 of 13 BFCL-v4 slots" on the open-weight side. — [BFCL-v4 leaderboard, llm-stats.com](https://llm-stats.com/benchmarks/bfcl-v4)
- Qwen3.5 BFCL-v4 (2026-07-18 snapshot): 397B-A17B 0.729, **27B 0.685**, **9B 0.661**, 4B 0.503, 2B 0.436 — [search synthesis citing BFCL-v4 2026-07-18 data, via benchlm.ai/llm-stats.com]. Note: the 27B score is for a size already eliminated on VRAM (Section B); **Qwen3.5-9B at 0.661 is the relevant number for the surviving candidate**.
- Qwen3-8B: reported BFCL-v3 at 66.3% in one source and 68.2% (thinking)/59.8% (non-thinking) in another, and BFCL-V4 at 42.6% in a third — [benchmarklist.com/models/qwen-qwen3-8b](https://benchmarklist.com/models/qwen-qwen3-8b/) and related search results. Scores disagree significantly across sources/conditions; treat the v4 figure (42.6%) as the more current but note the spread.
- DeepSeek-R1-0528-Qwen3-8B: BFCL_v3_MultiTurn = 37.0; Tau-Bench Airline 53.5, Retail 63.9 — [artificialanalysis.ai/models/deepseek-r1-qwen3-8b](https://artificialanalysis.ai/models/deepseek-r1-qwen3-8b). A vLLM GitHub issue, ["How to use DeepSeek-R1-0528-Qwen3-8B with function call" #19001](https://github.com/vllm-project/vllm/issues/19001), indicates real-world friction getting function-calling to work correctly with this model's chat template — worth checking before committing to it.
- Qwen2.5-14B-Instruct: no clean BFCL number found; one academic benchmark ("Benchmarking LLM Tool-Use in the Wild") reports fragmented single-digit-to-high-teens percentages across its own custom categories, which are not comparable to BFCL and are **not** a reliable proxy — [arXiv 2604.06185](https://arxiv.org/pdf/2604.06185). Older Qwen2.5 72B is reported competitive with GPT-4o on BFCL v4 in general commentary, but no specific 14B number was found.
- DeepSeek-R1-Distill-Qwen-14B: BFCL v3 = 53.5; DeepSeek-R1-Distill-Qwen-32B: BFCL v3 = 70.3 — [benchmarklist.com](https://benchmarklist.com/models/deepseek-r1-distill-qwen-14b/) (explicitly v3, not v4; context-gate status for these two models is unresolved per Section A, so these numbers are provided for completeness only, not as endorsement).

### Inferences
- Among context-gate-and-VRAM survivors, **Qwen3.5-9B (0.661 BFCL-v4)** currently has the most favorable *current-benchmark* tool-calling number with a clean sourcing trail.
- Qwen3-8B and DeepSeek-R1-0528-Qwen3-8B both show meaningfully lower/more scattered scores by comparison, and the latter has an open real-world integration complaint on GitHub.

### Gaps
- No BFCL-v4 number was found for Qwen2.5-14B-Instruct-1M or Qwen2.5-7B-Instruct-1M specifically (only the non-1M base size has indirect commentary).
- No benchmark number was found for DeepSeek-R1-Distill-Llama-8B/70B specifically (searches returned generic DeepSeek-R1 distill commentary, not isolated BFCL scores per size).

---

## Section D — llama.cpp support status

### Takeaway
Qwen3.5's hybrid-attention implementation in llama.cpp is new and had a confirmed, now-fixed crash bug under parallel/batched serving; Qwen3-Next support is merged and live; Qwen2.5-1M's DCA/sparse-attention extrapolation path is *not* implemented in llama.cpp, but this is irrelevant at the 64K gate since that model's real native 256K already covers 64K without DCA.

### Cited findings
- Qwen3.5 hybrid attention: GitHub issue [ggml-org/llama.cpp#20222](https://github.com/ggml-org/llama.cpp/issues/20222) — server crash ("Chunk not found") when reusing request slots under parallel load with Qwen3.5-35B. **Confirmed fixed** via PR #20232 (reporter verified under production load). Scope: **only affects parallel/batched serving** — single-request (`--parallel 1`) inference was stable throughout. A workaround (`--ctx-checkpoints 0 --no-cache-prompt`, costing ~1s/request) is documented for anyone who can't update immediately.
- Qwen3-Next: feature request [ggml-org/llama.cpp#15940](https://github.com/ggml-org/llama.cpp/issues/15940), merged via PR #16095; confirmed live in LM Studio's beta runtime channel. One known gap: the model ships an MTP (multi-token-prediction) head that llama.cpp does not yet use (perf-only, not a correctness issue).
- Qwen2.5-1M / Dual Chunk Attention: no llama.cpp implementation of DCA or the MInference sparse-attention prefill accelerator was found; these are documented as vLLM/BladeLLM-side features only. **This does not block the 64K gate** for Qwen2.5-14B/7B-1M because the real native 256K context already clears 64K using plain RoPE — DCA is only needed beyond 256K, which is out of scope for this requirement.
- Qwen3-8B / DeepSeek-R1-0528-Qwen3-8B: no model-specific llama.cpp issues surfaced in search beyond the general, long-standing Qwen3 support (merged since Qwen3's original release) — no special flags needed.

### Inferences
- The surviving dense/small candidates (Qwen3-8B-based, Qwen2.5-14B/7B-1M) need no non-default llama.cpp flags for the single-user Hermes use case.
- Qwen3.5-9B needs no workaround either, **provided Hermes only ever serves one request slot at a time** — if Hermes's local tier ever runs with `--parallel >1`, confirm the llama.cpp build includes PR #20232 (should be the case for any build from roughly September 2026 onward, but worth a version check before deployment).

### Gaps
- Did not independently verify whether llama.cpp's Qwen3.5/Qwen3.6 implementation actually gives the hybrid architecture its expected small/constant-size KV cache for linear-attention layers, or allocates something larger by default — this materially affects the real VRAM headroom claimed for Qwen3.5-9B in Section B and should be checked empirically (e.g. `llama-server --verbose` memory report) before relying on it.
- Qwen3.6-specific llama.cpp issues were not separately searched (budget); assumed to inherit Qwen3.5's support status given shared architecture, but this is an assumption, not a confirmed fact.

---

## Section E — Final shortlist (ranked, context-gate survivors only)

Ordered by: confirmed context-gate pass → fits 16GB VRAT at 64K → current tool-calling signal → llama.cpp cleanliness.

1. **Qwen3.5-9B** — native 262144 (inferred/high confidence from secondary sources), Q4_K_M 6.17GB + small hybrid-KV footprint, BFCL-v4 0.661, llama.cpp support present with a now-fixed parallel-serving bug (irrelevant if Hermes runs single-slot). **Best overall fit** given the VRAM headroom hybrid attention frees up, but carries the most architecture-maturity risk (newest model, newest llama.cpp code path) — verify actual KV behavior before committing.
2. **DeepSeek-R1-0528-Qwen3-8B** — native 32768 honestly extended to 131072 via self-documented YaRN (confirmed), Q4_K_M 5.03GB, fits 16GB comfortably even with fp16 KV cache, llama.cpp support mature (plain Qwen3 arch). Weaker/more scattered tool-calling numbers than Qwen3.5-9B, plus an open vLLM function-calling usability complaint (worth checking whether it also affects llama.cpp's chat-template handling before adopting).
3. **Qwen3-8B (plain, non-reasoning)** — same architecture/size/VRAM profile as #2 but native context is only 32768 unless YaRN is manually enabled in config (stock config ships `rope_scaling: null`) — **only passes the gate if YaRN is explicitly turned on**, which is a configuration step, not automatic. Listed below the R1-0528 variant because the latter ships the YaRN config already baked in.
4. **Qwen2.5-14B-Instruct-1M** — native 256K (confirmed from primary blog), but **only fits 16GB VRAM at 64K context if KV cache is quantized to Q8 or Q4** (default fp16 KV cache does not fit: ~21.9GB). Older architecture, weakest/least-documented current tool-calling numbers of the survivors. Usable but the tightest fit.
5. **Qwen2.5-7B-Instruct-1M** — same 256K native-context story as #4, smaller/cheaper, but VRAM fit and current tool-calling score were not independently verified (gap) — include only provisionally.
6. **DeepSeek-R1-Distill-Llama-8B** — context gate passes on solid architectural grounds (genuine Llama-3.1 128K continued-pretraining), but VRAM fit and current BFCL score were not independently verified (gaps) — include provisionally pending those checks.

**Explicitly excluded from the shortlist (not eliminated on the hard gate, but impractical):** Qwen3-Next-80B-A3B, Qwen3.5/3.6-27B, Qwen3.5/3.6-35B-A3B — all pass the context gate but cannot fit a 16GB RTX A4000 even weights-only at Q4_K_M.

**Unresolved, not placed on the shortlist either way:** DeepSeek-R1-Distill-Qwen-14B and -32B — the 131072 context claim in their config is unsubstantiated by any documented scaling mechanism, and the primary DeepSeek-R1 paper does not state a distillation training context length (the commonly-cited "32768" figure is actually an unrelated eval-time generation cap, confirmed by direct inspection of the paper). Needs an empirical long-context test before any decision.

**Eliminated, hard context-gate fail, confirmed:** every stock Qwen3 dense/MoE model (0.6B–235B-A22B) at real native 32768; every stock Qwen2.5 non-1M model at 32768; DeepSeek-R1-Distill-Qwen-1.5B/7B (Math base, native 4096); DeepSeek-V2-Lite (40x YaRN stretch from a 4096 base, not credible).

**Eliminated, no small variant exists:** DeepSeek-V3/V3.1/V3.2/R1 (full, non-distill) — smallest is ~671B total params.

**Not evaluated (logged as gap, not a verdict):** "Qwen3.8" / "Qwen3.8-Flash-Next" — found only as names in search results, no config or technical report retrieved.

---

## Overall gaps / open questions for the report writer or whoever acts next

1. **Needs empirical verification, not just doc-reading**: DeepSeek-R1-Distill-Qwen-14B/32B's real usable context — load in llama.cpp and run a needle-in-a-haystack test at 48K/64K before trusting the 131072 config number.
2. **Needs empirical verification**: whether llama.cpp's Qwen3.5/3.6 hybrid-attention code path actually gives the claimed small KV-cache footprint for linear-attention layers, or silently allocates full dense cache — this changes whether Qwen3.5-9B's VRAM headroom claim in Section B is real.
3. Not sized/benchmarked due to time budget: Qwen2.5-7B-Instruct-1M GGUF size, DeepSeek-R1-Distill-Llama-8B/70B GGUF size and current BFCL score.
4. "Qwen3.8" family — identity and specs unconfirmed; worth a dedicated follow-up if it turns out to be relevant (name suggests another hybrid "-Next"-style release).
5. No official Qwen3.5/Qwen3.6 technical-report PDF text was directly quoted (only secondary analyses) for the 262144 native-context claim — flagged throughout as "inferred" rather than "confirmed" for that reason.
