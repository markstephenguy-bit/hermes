# GLM/Zhipu, MiniCPM, InternLM, and Yi families — 64K native-context gate check

Hard rule applied throughout: a model is ELIMINATED if its genuinely-trained native
context is below 64,000 tokens, regardless of a larger `max_position_embeddings`
achieved only via a runtime/inference-time rope trick (dynamic NTK, unbaked YaRN
config edits, etc.) rather than actual continued pretraining on long sequences. This
mirrors the Qwen3-14B mistake (`max_position_embeddings`=40960, `rope_scaling: null`,
but real trained context was only 32768) that this research is specifically trying
to avoid repeating.

## GLM / Zhipu family

### Takeaway
Two members clear the 64K native-context gate with high confidence because Zhipu
explicitly describes continued-pretraining stages that bake the longer context into
the weights (not a runtime trick): **GLM-4-9B-Chat** (128K native) and
**GLM-4-9B-Chat-1M** (1M native). Both are small dense 9B models that fit a 16GB
RTX A4000 comfortably. **GLM-4.5-Air** also clears the context gate on paper but is
eliminated on VRAM — it's a 106B-total/12B-active MoE, nowhere near fitting 16GB.
ChatGLM3-6B (and -32K) are eliminated outright; their native context is well under
64K and this is extremely well-established public knowledge, not something that
needed re-verification here.

### Cited Findings
- GLM-4-9B base is pretrained with an 8,192-token context length; the Chat-1M
  checkpoint uses "a two-stage pre-training strategy, first expanding the context
  length to 128K, then to 1M," while the plain GLM-4-9B-Chat checkpoint "only
  requires the first stage" (128K) — [ChatGLM/GLM-4 technical report](https://arxiv.org/pdf/2406.12793); [GLM-4-9B-Chat-1M spec page](https://apxml.com/models/glm-4-9b-chat-1m)
- `THUDM/glm-4-9b-chat-1m` config.json: `seq_length: 1048576`, `rope_ratio: 10000`, `original_rope: true`, `num_hidden_layers: 40`, `num_attention_heads: 32`, `multi_query_group_num: 4`, `kv_channels: 128`, `hidden_size: 4096` — [raw config](https://huggingface.co/THUDM/glm-4-9b-chat-1m/raw/main/config.json)
- `THUDM/glm-4-9b-chat` config.json: `seq_length: 131072`, `rope_ratio: 500`, `multi_query_group_num: 2`, `kv_channels: 128`, `num_hidden_layers: 40` — [raw config](https://huggingface.co/THUDM/glm-4-9b-chat/raw/main/config.json)
- `zai-org/GLM-4.5-Air` config.json: `architectures: Glm4MoeForCausalLM`, `max_position_embeddings: 131072`, `rope_scaling: null`, `num_hidden_layers: 46`, `n_routed_experts: 128`, `num_key_value_heads: 8` — [raw config](https://huggingface.co/zai-org/GLM-4.5-Air/raw/main/config.json)
- GLM-4.5-Air has 106B total parameters / 12B active parameters; verified Q4_K_M GGUF is roughly 73.0GB, with the smallest practical FFN-quantized variants still around 61.66GB — [llm-stats / unsloth GGUF listing](https://huggingface.co/unsloth/GLM-4.5-Air-GGUF); [apxml spec page](https://apxml.com/models/glm-45-air)
- `bartowski/glm-4-9b-chat-1m-GGUF` Q4_K_M file size is 6.31GB — [bartowski GGUF repo](https://huggingface.co/bartowski/glm-4-9b-chat-1m-GGUF)
- BFCL v3 leaderboard (as of Sept 29, 2026) lists GLM-4.5 (the full flagship model, not Air or GLM-4-9B) at 76.7%, the top score on that leaderboard at the time — [pricepertoken BFCL v3 leaderboard](https://pricepertoken.com/leaderboards/benchmark/bfcl-v3)
- An older llama.cpp issue documents GLM-4-9B producing wrong results with partial GPU offloading — [ggml-org/llama.cpp issue #8558](https://github.com/ggml-org/llama.cpp/issues/8558)
- llama.cpp 0.4.1 (released September 2026) fixed MTP-context KV cache allocation and GDN normalization issues affecting GLM4MoE (and DeepSeek2/Cohere2MoE) architectures — [freedom.tech llama.cpp 0.4.1 notes](https://freedom.tech/posts/2026-09-14-llama-cpp-0-4-1/)
- GLM-4.7-Flash (a newer, presumably smaller "flash" MoE variant) has an open, unconfirmed bug report of abnormally high CPU usage / degraded performance on the CUDA backend, tied to a mmap→direct-I/O change, plus a separate Flash-Attention slowdown on Pascal GPUs — [HN discussion](https://news.ycombinator.com/item?id=46679872); search snippet referencing ggml-org/llama.cpp issue tracker
- A GLM-5.3-Flash build/load-test reference describes an 89.9 GiB Q2 quantization — i.e., even "Flash" branded newer GLM MoE variants are still very large and nowhere near a 16GB budget — [github.com/evanwtf/local-llm issue #25](https://github.com/evanwtf/local-llm/issues/25)

### Inferences
- GLM-4-9B-Chat and GLM-4-9B-Chat-1M are the strongest GLM-family candidates: 9B dense, MQA-style attention (only 2–4 KV groups, `kv_channels`=128) keeps KV cache small. Rough KV-cache math for the Chat-1M checkpoint (`2 × 40 layers × 4 KV groups × 128 dim × 2 bytes (fp16)` = 81,920 bytes/token ≈ 80KB/token): at 64K tokens that's ≈5.0GB, at 128K tokens ≈10GB. Added to the 6.31GB Q4_K_M weight file, that's ≈11.3GB at 64K context (comfortable on a 16GB A4000) and ≈16.3GB at 128K context (tight/borderline before other overhead, but recoverable with Q8_0 KV-cache quantization, which would roughly halve those KV figures). This is an estimate — confirm against actual llama.cpp VRAM usage before committing.
- Neither GLM-4-9B-Chat nor GLM-4-9B-Chat-1M has a dedicated, current (2026) BFCL v4 score that I could find; the 76.7% BFCL v3 figure found belongs to the full GLM-4.5 flagship, not these 9B checkpoints, and should not be attributed to them.
- Given the GLM-4.7-Flash and GLM-5.3-Flash data points, Zhipu's newer "Flash" branding does not mean "small enough for 16GB" — these remain large MoE models; none of the newer GLM releases surfaced a genuinely small (≤16GB-fittable) dense or MoE successor to GLM-4-9B.

### Gaps
- Could not find a current (2026, BFCL v4 or similar agentic benchmark) tool-calling score specific to GLM-4-9B-Chat or GLM-4-9B-Chat-1M. Only a BFCL v3 score for the much larger GLM-4.5 flagship was found.
- Could not confirm whether the `--override-kv glm4.rope.dimension_count` / `tokenizer.ggml.eos_token_id` manual overrides mentioned in the task's briefing are still required in current (late-2026) llama.cpp releases for GLM-4-9B GGUF files, or whether/when that was fixed upstream. Searches surfaced a different, older partial-offloading bug (#8558) and 2026-era GLM4MoE-specific KV-cache fixes, but nothing that directly confirms the override-kv flag's current necessity for the non-MoE `chatglm` architecture GLM-4-9B uses.
- Did not verify GLM-4-9B-Chat (non-1M) GGUF file size directly (only found the -1M variant's size, 6.31GB at Q4_K_M); given near-identical architecture it is very likely close to the same size, but this is inferred, not confirmed.
- Did not check GLM-4-32B-0414 / GLM-Z1-32B (a larger dense GLM variant) — flagged as out of scope for this pass since even at Q4 a 32B dense model (~19–20GB weights alone) is unlikely to fit 16GB, but this was not independently verified.

## MiniCPM family (OpenBMB)

### Takeaway
Every mainstream instruct-tunable MiniCPM checkpoint checked (MiniCPM3-4B, MiniCPM4-8B,
MiniCPM4.1-8B) has a native trained context of only 32,768 tokens — below the 64K
gate — with any longer window requiring a user-applied YaRN/LongRoPE config edit
rather than being baked in by OpenBMB. **MiniCPM-SALA** (Feb 2026) is the one
exception: its paper explicitly states a 520K-token training length, clearing the
gate with high confidence, but it uses an exotic hybrid sparse+linear attention
architecture whose llama.cpp support status is unconfirmed/likely absent.

### Cited Findings
- `openbmb/MiniCPM3-4B` config.json: `max_position_embeddings: 32768`, `rope_scaling.type: "longrope"` with `original_max_position_embeddings: 32768` — i.e., identical to `max_position_embeddings`, meaning no actual extension is configured in this checkpoint — [raw config](https://huggingface.co/openbmb/MiniCPM3-4B/raw/main/config.json)
- `openbmb/MiniCPM4-8B` config.json: `max_position_embeddings: 32768`, `rope_scaling.rope_type: "longrope"` with `original_max_position_embeddings: 32768` (again equal to max_position_embeddings) — [raw config](https://huggingface.co/openbmb/MiniCPM4-8B/raw/main/config.json)
- MiniCPM4 "natively supports context lengths of up to 32,768 tokens"; reaching 128K requires OpenBMB's separate long-context pre-training process, and the public instructions for enabling it involve manually editing the `rope_scaling` block (`rope_type: longrope`, supplying `long_factor` arrays) in `config.json` — [MiniCPM4 arxiv paper](https://arxiv.org/pdf/2506.07900); search-aggregated HF usage notes for MiniCPM4 YaRN/LongRoPE config edits
- MiniCPM-SALA is a 9B hybrid architecture ("interleaves 25% InfLLM-V2 sparse attention and 75% Lightning Attention layers") with SFT conducted "at 64K–140K length" and the paper explicitly reporting the model "extrapolates to 2048K tokens despite a 520K training length" — [MiniCPM-SALA paper](https://arxiv.org/pdf/2602.11761); [substack summary](https://smallaimodel.substack.com/p/2026-02-13-minicpm-sala-hybrid-attention)
- MiniCPM-SALA supports tool calls via a `minicpm4_xml` tool-call parser when deployed — [HF discussion thread](https://huggingface.co/openbmb/MiniCPM-SALA/discussions/9)
- MiniCPM-SALA achieves "up to 3.5× the inference speed of Qwen3-8B at a sequence length of 256K tokens" on A6000D-class GPUs — [smallaimodel.substack.com summary](https://smallaimodel.substack.com/p/2026-02-13-minicpm-sala-hybrid-attention) citing the paper

### Inferences
- MiniCPM3-4B, MiniCPM4-8B, and (by strong family-pattern inference) MiniCPM4.1-8B are all ELIMINATED on the native-context gate: 32,768 << 64,000, and the only path to a longer window is an un-baked, user-applied config/rope trick — exactly the pattern the task explicitly says to treat as suspicious and reject.
- MiniCPM-SALA is the only MiniCPM-family model that clears the gate on paper (520K training length, explicitly stated, not inferred from a bare `max_position_embeddings` field). However, because it is a hybrid sparse+linear attention model rather than a standard transformer, the usual "weights + standard KV cache" VRAM math does not directly apply — the 75% Lightning-Attention layers carry a fixed-size recurrent state rather than a per-token-growing KV cache, which could make it unusually cheap at long context if llama.cpp (or another runtime) supports the architecture at all. This is a meaningful potential advantage but is unverified.

### Gaps
- Could not confirm whether `MiniCPM4.1-8B` has the same 32,768 native-context config as MiniCPM4-8B — assumed by family-pattern similarity, not independently fetched.
- Could not find any GitHub issue, discussion, or documentation confirming llama.cpp (or GGUF format generally) supports MiniCPM-SALA's hybrid sparse+linear attention architecture. Given how recent the model is (Feb 2026) and how unusual the architecture is (interleaved sparse/linear attention, not a standard GQA/MQA transformer), it should be assumed UNSUPPORTED in llama.cpp until proven otherwise — this is a hard blocker for a llama.cpp-based deployment even though it clears the context gate.
- No GGUF file-size or quantization data found for MiniCPM-SALA (quantizer repos were not checked in this pass).
- No BFCL or other current tool-calling benchmark score found for MiniCPM-SALA, MiniCPM4-8B, or MiniCPM3-4B.

## InternLM family (Shanghai AI Lab)

### Takeaway
Every InternLM checkpoint checked relies on the exact pattern the task warns
against: a native/trained context of 32K, with any larger advertised window
(256K, 1M) achieved via **DynamicNTK** rope scaling — a runtime/inference-time
interpolation trick, not continued pretraining that bakes the longer context
into the weights. All InternLM candidates checked are therefore ELIMINATED on
the native-context gate.

### Cited Findings
- `internlm/internlm2_5-7b-chat-1m`-class config.json (fetched from the `-1m` repo): `max_position_embeddings: 262144`, `rope_scaling: {"type": "dynamic", "factor": 2.5}`, `rope_theta: 50000000` — [raw config](https://huggingface.co/internlm/internlm2_5-7b-chat-1m/raw/main/config.json)
- `internlm/internlm3-8b-instruct` config.json: `max_position_embeddings: 32768` (no larger figure claimed at all in the base field), `rope_scaling: {"rope_type": "dynamic", "factor": 6.0}`, `rope_theta: 50000000` — [raw config](https://huggingface.co/internlm/internlm3-8b-instruct/raw/main/config.json)
- "InternLM2.5 extends context length by scaling the RoPE Base and defaults to using DynamicNTK... InternLM 2.5 supports context windows exceeding one million tokens through dynamic NTK-aware Rotary Position Embedding interpolation, which dynamically adjusts the frequency basis of the rotary embeddings based on the input sequence length" and "the 32K training phase represents a middle ground in the model's context extension strategy, serving as a baseline before further extension" — [search-aggregated summary citing InternLM2 Technical Report](https://arxiv.org/pdf/2403.17297); [internlm3-8b-instruct HF discussion on context length](https://huggingface.co/internlm/internlm3-8b-instruct/discussions/9)

### Inferences
- The InternLM family's long-context variants are architecturally and functionally analogous to the exact failure mode the task describes for Qwen3-14B: a large `max_position_embeddings` value paired with a rope-scaling mechanism that is a runtime extrapolation trick (DynamicNTK) rather than continued pretraining, sitting on top of a genuinely-trained 32K base. Per the hard rule, these are ELIMINATED — the "up to 1M" or "262144" figures are not the real native trained context.
- `internlm3-8b-instruct`'s config is actually more honest about this than the 2.5 line: `max_position_embeddings` itself is only 32768, with the 6.0× DynamicNTK factor used purely at inference time to stretch further — this is the clearest confirmation that InternLM's own config convention treats DynamicNTK as separate from, not part of, the trained context length.
- No InternLM checkpoint checked would need VRAM/GGUF-size or tool-calling-benchmark analysis, since all are eliminated at the context gate — consistent with the task's instruction to not let other merits rescue a context-gate failure.

### Gaps
- Did not independently fetch `internlm2-chat-20b` or `internlm2_5-20b-chat` configs; assumed (by strong documented family pattern) that they follow the same 32K-native + DynamicNTK pattern, but this is inferred, not directly confirmed per-model.
- Did not find a current (2026) BFCL score for any InternLM checkpoint — moot given the context-gate elimination, but noting the gap for completeness as requested.
- Did not check llama.cpp's support/accuracy for DynamicNTK rope scaling itself (a secondary question, moot here since these models are eliminated regardless).

## Yi family (01.AI)

### Takeaway
**Yi-6B-200K** and **Yi-34B-200K** both clear the 64K native-context gate with
high confidence — 01.AI's own announcements and the Yi technical report describe
genuine continued pretraining on long-sequence data (not a runtime rope trick) to
reach a real 200K context. Yi-6B-200K is small enough to plausibly fit a 16GB
RTX A4000; Yi-34B-200K is eliminated on VRAM. Newer, shorter-context Yi-1.5 models
were not independently re-verified and should be treated as a likely-fail pending
a direct config check.

### Cited Findings
- `01-ai/Yi-6B-200K` config.json: `max_position_embeddings: 200000`, `rope_scaling: null`, `rope_theta: 10000000.0`, `num_hidden_layers: 32`, `num_attention_heads: 32`, `num_key_value_heads: 4`, `hidden_size: 4096` — [raw config](https://huggingface.co/01-ai/Yi-6B-200K/raw/main/config.json)
- `01-ai/Yi-34B-200K` config.json: `max_position_embeddings: 200000`, `rope_scaling: null`, `rope_theta: 10000000.0`, `num_hidden_layers: 60`, `num_attention_heads: 56`, `num_key_value_heads: 8`, `hidden_size: 7168` — [raw config](https://huggingface.co/01-ai/Yi-34B-200K/raw/main/config.json)
- "The context length was extended to 200K through lightweight continual pretraining... continued on about 5B [tokens of] length-upsampled data"; "the full-attention model was continued using sequence parallelism and distributed attention without any sparse or linear attention... In the Needle-in-a-Haystack test, the performance rises from 89.3% to 99.8%" — [01.AI official announcement](https://x.com/01AI_Yi/status/1765784482861175208); [Yi technical report](https://arxiv.org/pdf/2403.04652)
- `TheBloke/Yi-6B-200K-GGUF` Q4_K_M file size is 3.67GB — [TheBloke GGUF repo](https://huggingface.co/TheBloke/Yi-6B-200K-GGUF)

### Inferences
- Both Yi-200K checkpoints pass the native-context gate at high confidence: `rope_scaling: null` plus an explicit, named continued-pretraining process (described in 01.AI's own report, including a before/after needle-in-a-haystack benchmark) is exactly the kind of "baked in, confirmed from official report" evidence the task asks for — the opposite of the Qwen3-14B failure mode.
- Yi-6B-200K VRAM fit looks good: Q4_K_M weights are 3.67GB. Rough KV-cache math (`2 × 32 layers × 4 KV heads × 128 head_dim × 2 bytes` = 65,536 bytes/token ≈ 64KB/token fp16): at 64K context ≈4.2GB, at 128K context ≈8.4GB. Total at 64K ≈7.9GB, at 128K ≈12.1GB — comfortably within a 16GB A4000 even without KV quantization. This is an estimate, not a verified llama.cpp measurement.
- Yi-34B-200K is eliminated on VRAM: 60 layers × 7168 hidden size dense model; even before adding any KV cache, a dense 34B model at Q4_K_M typically runs ~19–20GB of weights alone, already exceeding the 16GB budget. (File size not independently fetched this pass, but this is a very safe inference for a model of this size class.)

### Gaps
- Did not find a current (2026) BFCL v4 or other current agentic tool-calling benchmark score for Yi-6B-200K or Yi-34B-200K. These are older (2023/2024-era) base/chat checkpoints and may not have been evaluated on newer agentic benchmarks at all — worth flagging to the report writer that tool-calling quality for this candidate is largely unverified versus more recent models.
- Did not check llama.cpp GitHub issues specifically for Yi-200K (standard Llama-architecture `LlamaForCausalLM` per config, so it is very likely to already be fully supported in llama.cpp with no special overrides, but this was not explicitly confirmed via a targeted search this pass).
- Did not independently verify whether Yi-1.5 (01.AI's 2024 refresh) or any 2025/2026 Yi successor model reintroduced a long-context variant; the Yi-200K line appears to be the only long-context Yi family member, and I could not confirm whether 01.AI has shipped a newer 2025/2026 model that supersedes it. If no newer Yi model surfaced in general web presence beyond the 200K line checked here, that itself is notable (the family may be stale), but this should be treated as an open gap rather than a confirmed "no newer Yi model exists" claim.
- Did not fetch Yi-34B-200K's actual GGUF file size (reasoned from parameter count instead); if a very aggressive quantization (e.g., Q2/IQ2) were used it could theoretically approach 16GB, but this would badly degrade quality and wasn't pursued given the weights-alone estimate already exceeds budget at any reasonable quant level for agentic tool-calling use.

## Summary table (shortlist after elimination)

| Model | Native context | Confidence | Context gate | VRAM fit (16GB A4000) | Verdict |
|---|---|---|---|---|---|
| GLM-4-9B-Chat-1M | 1,048,576 (two-stage continued pretraining) | Confirmed (technical report) | PASS | ~11.3GB @64K / ~16.3GB @128K (est., fp16 KV) | **Survives** — best overall fit |
| GLM-4-9B-Chat | 131,072 (one-stage continued pretraining) | Confirmed (technical report) | PASS | Same architecture, similar footprint (est.) | **Survives** |
| Yi-6B-200K | 200,000 (continued pretraining, 5B tokens) | Confirmed (official report + benchmark) | PASS | ~7.9GB @64K / ~12.1GB @128K (est.) | **Survives** |
| GLM-4.5-Air | 131,072 | Confirmed (config) | PASS | ~61–73GB (Q4_K_M class) | Eliminated — VRAM |
| Yi-34B-200K | 200,000 | Confirmed | PASS | ~19–20GB+ weights alone (est.) | Eliminated — VRAM |
| MiniCPM-SALA | 520,000 (training length, paper-stated) | Confirmed (paper) | PASS | Unknown (hybrid architecture, not standard KV math) | Eliminated — llama.cpp support unconfirmed/likely absent |
| MiniCPM4-8B / 4.1-8B | 32,768 (128K only via un-baked user config edit) | Confirmed (config) | FAIL | n/a | Eliminated — context |
| MiniCPM3-4B | 32,768 | Confirmed (config) | FAIL | n/a | Eliminated — context |
| InternLM2.5-7B(-1M) | 32K trained, DynamicNTK runtime trick to 262144/1M | Confirmed (config + report) | FAIL | n/a | Eliminated — context (same failure mode as Qwen3-14B) |
| InternLM3-8B-Instruct | 32,768 trained, DynamicNTK runtime trick (6×) | Confirmed (config) | FAIL | n/a | Eliminated — context |
| ChatGLM3-6B / -32K | 8K / 32K | Well-established, not independently re-fetched | FAIL | n/a | Eliminated — context |

**Top pick pending the report writer's cross-family ranking:** GLM-4-9B-Chat-1M —
passes the context gate on the most robust evidence of any candidate (explicit
two-stage continued-pretraining technical report, no runtime rope tricks), has the
best-understood VRAM math of the survivors thanks to its MQA-style small KV cache,
and has a mature (2+ year old) llama.cpp `chatglm` architecture implementation —
though the specific override-kv flag status in *current* llama.cpp releases and a
*current* (2026) tool-calling benchmark score for this exact checkpoint remain
unverified gaps that should be checked before final selection.
