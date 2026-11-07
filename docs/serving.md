# Serving Qwen3.5-4B for the swarm (vLLM on WSL2, RTX 5070 Laptop)

All swarm agents share **one local OpenAI-compatible vLLM server**. This page records the versions, the exact commands,
the measured capacity, throughput and numerical fidelity of each serving option, and the problems hit along the way.
Everything here was measured on 2026-11-07.

**TL;DR**

| | |
|---|---|
| Endpoint | `http://localhost:8000/v1`, reachable from Windows and from WSL (WSL runs with `networkingMode=mirrored`) |
| Served model name | `cyankiwi/Qwen3.5-4B-AWQ-4bit` (matches `LLM_MODEL` in `src/swarm_epi/config.py`) |
| Engine | **vLLM 0.33.0** in WSL2 Ubuntu 24.04, PyTorch 2.14.0+cu132, native `sm_120` kernels. vLLM works; the llama.cpp fallback was not needed |
| Start | one-time `bash scripts/setup_vllm.sh`, then `bash scripts/serve_vllm.sh`, both inside WSL. Ready after 2 min 52 s cold, 67 s warm |
| Thinking | off: server default `--default-chat-template-kwargs '{"enable_thinking": false}'`; clients also send `chat_template_kwargs` |
| Default config | bf16 KV cache, **bf16 Gated-DeltaNet state**, **prefix caching off**, KV cache pinned at 1.25 GiB, `--max-num-seqs 64` |
| Throughput (default) | ~2k-token prompt / 400-token output requests: **340.0 / 338.0 gen tok/s at 32 concurrent** (≈2,000 total tok/s, 37.7 s wall); **357.4 / 356.6 gen tok/s at 64 concurrent** (≈2,110 total tok/s, 71.7 s wall); 367.6 gen tok/s with 128 queued. Swarm-shaped 4-call agent loop: **222.4 gen tok/s = 14.0 agents/min** |
| Did fp8 KV / prefix caching help? | **No** in the configuration that keeps the model's answers unchanged. fp8 KV fits more requests but changed answers (probe shifted up to 0.57, 2/24 flips). Prefix caching got a 0% hit rate on the swarm loop and cost 1–17% throughput (§5) |
| Client request shape | verified: `extra_body={"chat_template_kwargs":{"enable_thinking":false},"top_k":20,"min_p":0}`, `presence_penalty`, per-request `seed` (two identical seeded requests return identical text), `logprobs` with **`top_logprobs=20` accepted** (21 → HTTP 400, `--max-logprobs 20`). Logprobs are `raw_logprobs` (vLLM default), i.e. not affected by temperature/top_k/top_p/penalties |
| Max concurrency (default) | vLLM log: `GPU KV cache size: 32,336 tokens, Maximum concurrency for 4,096 tokens per request: 7.89x`. Observed: up to **13** requests of ~2.4k tokens running at once, the rest queued, no preemptions |
| Originally requested flags | `--kv-cache-dtype fp8 --enable-prefix-caching` works, but logged `GPU KV cache size: 23,630 tokens, Maximum concurrency for 4,096 tokens per request: 5.77x` and was 27% slower than the default in the same sweep (251.6 vs 344.1 gen tok/s). fp8 KV also changed the model's answers measurably, so it is off by default (§5) |

## 1. Hardware and software stack

| Component | Version / value |
|---|---|
| GPU | NVIDIA GeForce RTX 5070 Laptop GPU, 8 GB (8151 MiB), compute capability 12.0 (`sm_120`, Blackwell consumer) |
| Windows driver | 617.42 (KMD); WSL `nvidia-smi` shows CUDA UMD 13.4 and NVML 615.78.05 |
| Host | Windows 11 Home 10.0.26200, WSL2 kernel 6.18.54.1-microsoft-standard-WSL2, Ubuntu 24.04.5, 15.3 GiB RAM visible in WSL |
| GPU memory held by Windows before the server starts | 720–1,710 MiB, drifting during the session (see Problem 3) |
| Python / uv | CPython 3.12.3 (Ubuntu system), uv 0.13.6 |
| vLLM | **0.33.0** (PyPI, 2026-11-02; GitHub tag [`v0.33.0rc3`](https://github.com/vllm-project/vllm/releases/tag/v0.33.0rc3)); release wheels are CUDA 13.0 only |
| PyTorch / Triton | torch 2.14.0+cu132 (arch list includes `sm_120`), triton 3.8.0 |
| FlashInfer | flashinfer-python 0.7.2.post1, plus `flashinfer-jit-cache-sm120f` 0.7.2.post1+cu130 from `vllm download-kernels` |
| transformers / compressed-tensors / openai | 5.20.2 / 0.17.0 / 3.46.0 |
| Model | [`cyankiwi/Qwen3.5-4B-AWQ-4bit`](https://huggingface.co/cyankiwi/Qwen3.5-4B-AWQ-4bit), snapshot `d3e78b50c727b1f34802f440ca84b25781625352`, Apache-2.0. The fallback [`RedHatAI/Qwen3.5-4B-quantized.w4a16`](https://huggingface.co/RedHatAI/Qwen3.5-4B-quantized.w4a16) was not needed and was not tested |

**Model facts that set the memory budget** (from the checkpoint's `config.json` and the
[Qwen3.5-4B card](https://huggingface.co/Qwen/Qwen3.5-4B)):

- Architecture: `Qwen3_5ForConditionalGeneration`, 32 layers in the layout 8 × (3 × Gated DeltaNet → 1 × Gated Attention).
- Only the **8 full-attention layers** keep a per-token KV cache (4 KV heads, head dim 256).
- The **24 Gated-DeltaNet (linear-attention) layers** each keep a fixed recurrent state per sequence: 32 value heads × 128 × 128,
  declared **float32** (`mamba_ssm_dtype: "float32"`).
- Vocabulary 248,320, tied embeddings.
- Quantization: llm-compressor AWQ, `compressed-tensors` `pack-quantized`, int4 symmetric, group size 32. The vision tower,
  `lm_head`, `mtp.fc` and the GDN `in_proj_a/in_proj_b` stay unquantized.
- Size: 3.76 GiB on disk. With `--language-model-only` vLLM puts **3.2 GiB** of weights on the GPU
  (`Model loading took 3.2 GiB memory`), using the Marlin int4 kernel (`Using MarlinLinearKernel for CompressedTensorsWNA16`).

Per-sequence memory, derived from those numbers:

| Item | Size |
|---|---|
| Attention KV per token (8 layers × K+V × 4 heads × 256) | 32 KiB bf16, 16 KiB fp8 |
| Gated-DeltaNet state per sequence (24 layers × 32 × 128 × 128) | 48 MiB fp32 (model-native), 24 MiB bf16, plus a small conv state |
| One ~2.4k-token swarm request (2k prompt + 400 output) | ≈ 75 MiB KV (bf16) + 48 MiB state (fp32) ≈ 123 MiB; ≈ 99 MiB with bf16 state |

The recurrent state, not the KV cache, is the largest per-sequence item. vLLM's hybrid KV-cache manager gives attention
pages and GDN-state pages one common page size by growing the attention block size
([design doc](https://docs.vllm.ai/en/latest/design/hybrid_kv_cache_manager.html)). That is why the logs report blocks of
272–1088 tokens, e.g. `Setting attention block size to 1088 tokens to ensure that attention page size is >= mamba page size`.

## 2. Install (once)

Inside WSL, from the repo checkout under `/mnt/c/...`:

```bash
bash scripts/setup_vllm.sh
```

What [`scripts/setup_vllm.sh`](../scripts/setup_vllm.sh) does (every line is commented with its source):

1. `uv venv ~/projects/agent-swarm-epi/vllm-env --python 3.12 --seed`, on the WSL ext4 disk rather than `/mnt/c`.
2. `uv pip install "vllm==0.33.0" --torch-backend=auto`. This resolves 199 packages including torch 2.14.0+cu132; preparing
   them took 12 min 37 s here (download-bound). No nightly and no source build are needed: `qwen3_5` is supported in the
   release, and the wheels include `sm_120` ([vLLM GPU install guide](https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html)).
3. `vllm download-kernels`, which installs FlashInfer's precompiled kernels including `sm120f` (8 min 39 s). Without it vLLM
   warns `FlashInfer kernels are disabled: flashinfer-cubin is not installed and nvcc ... is missing`, and this machine has
   no `nvcc`.
4. `hf download cyankiwi/Qwen3.5-4B-AWQ-4bit` with `HF_HOME=~/projects/agent-swarm-epi/hf-cache`.

## 3. Serve

```bash
bash scripts/serve_vllm.sh          # inside WSL; extra args are appended to `vllm serve`
```

With its defaults, [`scripts/serve_vllm.sh`](../scripts/serve_vllm.sh) runs:

```bash
HF_HOME=~/projects/agent-swarm-epi/hf-cache HF_HUB_OFFLINE=1 \
vllm serve cyankiwi/Qwen3.5-4B-AWQ-4bit \
  --language-model-only \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.8 \
  --kv-cache-dtype auto \
  --mamba-ssm-cache-dtype bfloat16 \
  --no-enable-prefix-caching \
  --max-num-seqs 64 \
  --kv-cache-memory-bytes 1342177280 \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --port 8000
```

Differences from the originally requested command (`--gpu-memory-utilization 0.8 --enable-prefix-caching`, plus
`--kv-cache-dtype fp8` only if it works). Each is backed by measurements in §5–6, and each can be switched back with an env var:

| Change | Why | Revert with |
|---|---|---|
| `--max-num-seqs 64` | the default 256 does not start (Problem 1) | `MAX_NUM_SEQS=...` |
| `--kv-cache-memory-bytes 1342177280` | `--gpu-memory-utilization` sizing is not reproducible under WSL (Problem 3) | `KV_CACHE_BYTES=""` |
| fp8 KV off | runs, but slower in the original config and changes answers (probe shifted up to 0.57, 2/24 flips) | `KV_DTYPE=fp8` |
| prefix caching off | 0% hit rate on the swarm-shaped loop, 1–17% slower, one large probe outlier when combined with bf16 state | `PREFIX_CACHE=1` |
| bf16 Gated-DeltaNet state | +19% single-turn, +9% agent-loop throughput; probe shift within serving noise | `SSM_DTYPE=auto` (model-native fp32) |

Startup: the first (cold) start took 2 min 52 s, of which `torch.compile` was 43 s and the first profiling/warmup 29–35 s.
Warm restarts take 67 s (compile cache hit, weights 1.3 s from page cache). The server is ready when the log prints
`Application startup complete.` Logs go to `~/projects/agent-swarm-epi/logs/vllm_serve_<timestamp>.log`.

### Client settings (what the orchestrator sends)

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
r = client.chat.completions.create(
    model="cyankiwi/Qwen3.5-4B-AWQ-4bit",
    messages=[{"role": "user", "content": "..."}],
    temperature=0.7, top_p=0.8, presence_penalty=1.5, max_tokens=768,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}, "top_k": 20, "min_p": 0.0},
)
# Belief probe: one token, top-5 logprobs
p = client.chat.completions.create(..., max_tokens=1, logprobs=True, top_logprobs=5, temperature=0.0)
```

The sampling values are the Qwen3.5 card's "Instruct (or non-thinking) mode for general tasks" settings
([card](https://huggingface.co/Qwen/Qwen3.5-4B)). `top_k`, `min_p`, `ignore_eos`, `min_tokens` and `chat_template_kwargs`
are vLLM extensions passed through `extra_body`
([OpenAI-compatible server, "Extra parameters"](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)).
Checked on the running default server with `client_check.py` (shared notes, `serving/`), using exactly the orchestrator's
request shape (the `extra_body` above plus `presence_penalty=1.5`, `seed=1234`, `logprobs=True`):

- **`top_logprobs=20` is accepted** and returns 20 entries. `top_logprobs=21` is rejected with
  `400 - Requested sample logprobs of 21, which is greater than max allowed: 20` (`--max-logprobs` default 20).
- **Per-request `seed` works.** Two sequential identical requests with `seed=1234` at T=0.7 returned identical text.
  Under concurrent load, batch composition can still change the numerics (§7).
- **Returned logprobs are raw.** vLLM's `--logprobs-mode` default is `raw_logprobs` ("the values before applying any logit
  processors"). The probe's P(Yes) is therefore the model's own distribution, not the temperature/top_k/penalty-processed
  one.

## 4. Smoke tests (pass)

Script: `smoke_test_vllm.py` (see Artifacts). It ran from **Windows**
(`uv run --no-project --with openai python smoke_test_vllm.py`) and from **WSL** (the vLLM venv's python), both against
`localhost:8000`, on every server configuration below. Results on the final default server:

| Test | Result (identical from Windows and WSL) |
|---|---|
| Chat completion, thinking off, T=0.7, top_p=0.8, top_k=20, presence_penalty=1.5 | `finish_reason=stop`, 24 prompt + 63–67 completion tokens, **no `<think>`/`</think>` in the content and no reasoning field** |
| Same request **without** `chat_template_kwargs` (server default only; checked on the first server) | no `<think>`; 24 prompt tokens, the same as with the kwarg, because the template inserts the empty think block |
| `logprobs=True, top_logprobs=5, max_tokens=1`, Yes/No question, T=0 | top-5 = `No` 0.9706, `Yes` 0.0201, ` No` 0.0084, ` Yes` 0.0003, `no` 0.0001; 0.9996 of the mass is on Yes/No variants |

Notes for the belief probe:

- Yes/No come in several tokenizations (`Yes`, ` Yes`, `no`), so sum the variants and renormalise over {Yes, No}.
- On the first (fp8-KV) server, `<think>` showed up in the top-5 with probability 0.0001.
- Probe values depend slightly on server dtypes (§5), so keep one fixed server config for the whole experiment.

## 5. Throughput, capacity and fidelity of the serving options

**Workloads.**

- **Single-turn:** 32 concurrent chat requests. Each has a distinct ~1,967-token prompt (synthetic message-board posts,
  chat template included) and exactly 400 output tokens, forced with `ignore_eos=true, min_tokens=400`. Aggregate
  generated tok/s = 12,800 / wall time from first send to last response. Run twice per server start.
- **128-request:** the same, with 128 requests (about 4 swarms' worth queued).
- **Agent loop (swarm-shaped):** 32 agents in parallel. Each runs a 4-call conversation that shares a growing prefix:
  solve (400 out) → grader feedback and retry (400 out) → post + notes (150 out) → Yes/No probe (1 token, logprobs).
  That is 950 generated tokens per agent.

**Fidelity check.** 24 long (~2k-token) board prompts, each with a Yes/No question whose answer is uncertain (reference
P(Yes) ranges 0.23–0.85). For each prompt the check records P(Yes) from the top-20 logprobs at T=0, plus a greedy
128-token answer. Reference configs: E (bf16 KV, fp32 state) for the batched runs, F for the batch-size-1 runs.

**Controls.**

- Every config is a fresh server start with the KV cache pinned at 1.25 GiB.
- Peak GPU memory comes from `nvidia-smi` sampled every 0.5 s and includes Windows' own use.
- The same config was restarted to check variation between starts (B/E: 276.1 vs 287.0 mean gen tok/s, about 4%).
- vLLM is not batch-invariant, so the fidelity set was also run sequentially (batch size 1), where a rerun is
  bit-identical.

All tables below are printed by `summarize_serving.py` from the raw result files (no hand-typed numbers).

**Configs (all: KV pinned 1.25 GiB, `--max-num-seqs 64`; "n/m" = not measured in that run):**

| Config | KV dtype | Prefix cache | GDN state | Block (tokens) | KV cache tokens / "Max concurrency @4096" | Max running | Single-turn gen tok/s (runs) | 128-req gen tok/s | Agent-loop gen tok/s | Agents/min | Prefix hit rate | Peak GPU MiB | Probe mean / max abs dP(Yes) vs E | Yes/No flips |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | fp8 | on | fp32 | 1088 | 23,630 / 5.77x | 14 | 252.2 / 251.1 (mean 251.6) | 250.2 | n/m | n/m | n/m | 7289 | n/m | n/m |
| B | bf16 | on | fp32 | 576 | 17,106 / 4.18x | 9 | 279.6 / 272.5 (mean 276.1) | n/m | n/m | n/m | n/m | 6569 | n/m | n/m |
| C | fp8 | off | fp32 | 1056 | 45,056 / 11.00x | 14 | 301.6 / 303.0 (mean 302.3) | n/m | n/m | n/m | n/m | 7195 | n/m | n/m |
| D | fp8 | on | bf16 | 576 | 34,213 / 8.35x | 19 | 418.2 / 408.3 (mean 413.2) | n/m | n/m | n/m | n/m | 7090 | n/m | n/m |
| E | bf16 | on | fp32 | 576 | 17,106 / 4.18x | 9 | 288.7 / 285.3 (mean 287.0) | n/m | 192.9 | 12.2 | 0.0 | n/m | 0.0 / 0.0 (rerun) | 0 |
| F | bf16 | off | fp32 | 528 | 28,672 / 7.00x | 10 | 290.9 / 289.7 (mean 290.3) | n/m | 201.5 | 12.7 | 0.0 | n/m | 0.0135 / 0.0702 | 0 |
| **G (default)** | bf16 | off | bf16 | 272 | 32,336 / 7.89x | 13 | 353.5 / 334.8 (mean 344.1) | n/m | 218.9 | 13.8 | 0.0 | n/m | 0.0099 / 0.045 | 0 |
| H | bf16 | on | bf16 | 320 | 23,831 / 5.82x | 12 | 338.5 / 339.3 (mean 338.9) | n/m | 204.4 | 12.9 | 0.0 | n/m | 0.0312 / 0.4721 | 1 |
| I | fp8 | off | bf16 | 544 | 55,854 / 13.64x | 21 | 417.9 / 417.0 (mean 417.4) | n/m | 250.7 | 15.8 | 0.0 | n/m | 0.0387 / 0.4613 | 1 |
| J | fp8 | off | fp32 | 1056 | 45,056 / 11.00x | 15 | 333.7 / 336.4 (mean 335.0) | n/m | 229.5 | 14.5 | 0.0 | n/m | 0.0368 / 0.443 | 1 |

**Batched fidelity, pairwise** (mean / max |ΔP(Yes)| over 24 prompts, the 24 requests sent concurrently):

| | E | F | G | H | I | J |
|---|---|---|---|---|---|---|
| E | — | 0.013 / 0.070 | 0.010 / 0.045 | 0.031 / 0.472 | 0.039 / 0.461 | 0.037 / 0.443 |
| F | 0.013 / 0.070 | — | 0.017 / 0.115 | 0.029 / 0.457 | 0.041 / 0.446 | 0.038 / 0.427 |
| G | 0.010 / 0.045 | 0.017 / 0.115 | — | 0.036 / 0.487 | 0.041 / 0.477 | 0.036 / 0.458 |
| H | 0.031 / 0.472 | 0.029 / 0.457 | 0.036 / 0.487 | — | 0.022 / 0.058 | 0.021 / 0.044 |
| I | 0.039 / 0.461 | 0.041 / 0.446 | 0.041 / 0.477 | 0.022 / 0.058 | — | 0.016 / 0.051 |
| J | 0.037 / 0.443 | 0.038 / 0.427 | 0.036 / 0.458 | 0.021 / 0.044 | 0.016 / 0.051 | — |

**Batch-size-1 fidelity vs F** (bf16 KV, fp32 state = model-native dtypes; prefix caching off; requests sent one at a time):

| Compared run | KV dtype | GDN state | mean / max abs dP(Yes) | Yes/No flips | greedy exact (of 24) | greedy common prefix / length (chars) |
|---|---|---|---|---|---|---|
| F | bf16 | fp32 (rerun) | 0.0 / 0.0 | 0 | 24 | 591.8 / 591.8 |
| G | bf16 | bf16 | 0.0109 / 0.0603 | 0 | 10 | 405.4 / 591.8 |
| J | fp8 | fp32 | 0.0728 / 0.5744 | 2 | 3 | 287.9 / 591.8 |
| I | fp8 | bf16 | 0.0392 / 0.412 | 1 | 2 | 279.8 / 591.8 |

**Final validation of the default server** (`scripts/serve_vllm.sh` defaults, after the sweep):

| Client | Test | Result |
|---|---|---|
| Windows | n=32 single-turn | gen 340.0 tok/s, wall 37.65 s, total 2011.5 tok/s, p50 latency 28.44 s |
| Windows | 32-agent 4-call loop | gen 222.4 tok/s, wall 136.71 s, 14.0 agents/min, prefix hit rate 0.0 |
| Windows | n=32 single-turn | gen 338.0 tok/s, wall 37.86 s, total 2000.0 tok/s, p50 latency 28.61 s |
| WSL | n=128 single-turn | gen 367.6 tok/s, wall 139.27 s, total 2173.9 tok/s, p50 latency 79.61 s |
| WSL | n=64 single-turn | gen 357.4 tok/s, wall 71.62 s, total 2114.6 tok/s, p50 latency 41.71 s |
| WSL | n=64 single-turn | gen 356.6 tok/s, wall 71.79 s, total 2109.6 tok/s, p50 latency 41.85 s |
| WSL | server during the runs above | peak 6,322 MiB of 8,151 (includes Windows' own use; sampled during the n=32/loop/n=128 runs), max 13 requests running (also during n=64) |

**What the data say.**

1. **The workload is prefill-heavy and capacity-bound.**
   - Each 32-request test processes ~63k prompt tokens against 12.8k generated tokens.
   - Only 9–21 requests fit at once, and the rest queue.
   - Throughput therefore tracks how many sequences fit *and* how fast prefill runs, not decode speed alone.
2. **fp8 KV is not a free win.**
   - With fp32 state, fp8 KV fits more requests (14 vs 9) but was slower with prefix caching on (A 251.6 vs B/E 276–287).
     It was faster with prefix caching off (J 335.0 vs F 290.3), and fastest combined with bf16 state (I 417.4).
   - It perturbs the model clearly. At batch size 1, a single-factor change from F to J moves P(Yes) by mean 0.073, max
     0.574, and flips 2 of 24 Yes/No answers; only 3 of 24 greedy answers stay identical.
   - Cause: unscaled e4m3 KV. The checkpoint ships no KV scales, and vLLM logs `it may cause accuracy drop without a
     proper scaling factor` ([docs](https://docs.vllm.ai/en/latest/features/quantization/quantized_kvcache.html)).
   - Verdict: fp8 KV runs, but it changes the agents' behaviour, so it failed "keep it only if it works".
3. **bf16 Gated-DeltaNet state is the cheap win.**
   - It halves the largest per-sequence item, from 48 to 24 MiB.
   - Throughput gain G vs F: single-turn +18.5% (344.1 vs 290.3), agent loop +8.6% (218.9 vs 201.5).
   - Fidelity at batch size 1, G vs F: mean |ΔP| 0.011, max 0.060, no flips. That is the same size as the change caused
     by merely toggling prefix caching (E vs F batched: 0.013 / 0.070), i.e. within ordinary batched-serving noise.
   - Evidence strength: suggestive, from 24 prompts of ~2k tokens with ≤128 decoded tokens. Longer decode horizons
     were not tested.
4. **Prefix caching does not help this workload.**
   - The hit rate was 0.0 in both agent-loop runs with caching on (E and H).
   - Two likely causes:
     - Qwen's chat template re-renders earlier assistant turns without the empty `<think></think>` block, so the token
       stream diverges right after the first user prompt.
     - The 1.25 GiB cache holds only 9–21 sequences and 20+ requests are queued, so freed blocks are reused before an
       agent's next call arrives.
   - vLLM only caches full blocks ([design](https://docs.vllm.ai/en/latest/design/prefix_caching.html)), and the hybrid
     model's blocks are 272–1088 tokens, so short shared system prompts cannot hit anyway.
   - Caching costs 1% (F vs E, single-turn) to 17% (C vs A).
   - Combined with bf16 state (H), one probe moved from 0.44 to 0.91 vs every other bf16-KV config. Untested hypothesis:
     "align"-mode state checkpoints at block boundaries round the state more often.
5. **Decision rule.** It was written down after the batched E/F/G fidelity results were seen, and before the H/I/J results
   and the batch-size-1 check were run, so it is not blind to G. Rule: take the fastest agent-loop config whose
   probe deviation from the reference stays within the E-vs-F band (mean ≤ 0.014, max ≤ 0.07, no flips). G passes in both
   the batched and the batch-size-1 test. I, J and H fail. **G is the default.**
6. **Estimate for the experiment:** 13.8–14.0 agents/min on the 4-call loop means about 2.3 min per 32-agent swarm round
   with these forced lengths. Natural-EOS outputs should be shorter. Running several swarms at once adds little throughput
   (single-turn 32 → 64 → 128 requests: 339 → 357 → 368 gen tok/s), so total time scales roughly with total agent-rounds.
7. **Prompt length.** Swarm prompts are 1–3k tokens plus ≤768 output (the code-answer cap was raised from 384 after the
   smoke test, where 40/59 answers hit 384). The client asks vLLM's `/tokenize` for the exact prompt length and clamps
   `max_tokens` so every request fits `--max-model-len 4096` (`LLM._fit_budget`). Longer prompts mean fewer requests in flight: each ~3.4k-token request needs ~1.4× the attention
   KV of the 2.4k-token test request, while the GDN state stays fixed per sequence.

## 6. Problems and fixes

1. **`ValueError: max_num_seqs (256) exceeds available Mamba cache blocks (93)`** on the first start.
   - Cause: vLLM 0.33 needs one GDN-state block per decoding sequence before it captures CUDA graphs. The default 256
     also meant capturing 51 graph sizes (188 s).
   - **Fix:** `--max-num-seqs 64`, above the 9–21 requests that fit anyway.
2. **FlashInfer kernels disabled** (`flashinfer-cubin is not installed and nvcc ... is missing`).
   - **Fix:** `vllm download-kernels` (installs `flashinfer-jit-cache-sm120f`).
   - The log then shows the FlashInfer GDN prefill kernel, FlashInfer attention (`decode_backend=xqa ... arch=sm120` with
     fp8 KV), and FlashInfer top-k/top-p sampling.
3. **The KV-cache size changed between near-identical starts:** 1.25 GiB, then 0.79 GiB, with only `--max-num-seqs`
   changed.
   - vLLM's startup profiler measured "peak activation" as 1.73 GiB in one start and 2.21 GiB in the next. Its
     CUDA-graph estimates were 0.54 and 1.04 GiB, for graphs that actually took 0.18 and 0.07 GiB.
   - Cause: under WSL the profiler sees whole-GPU free memory, so GPU allocations by Windows apps during profiling are
     billed to vLLM. Windows' own GPU use drifted between 720 and 1,710 MiB during this session.
   - vLLM's own log points at the fix: `Replace gpu_memory_utilization config with --kv-cache-memory=...`.
   - **Fix:** pin `--kv-cache-memory-bytes 1342177280` (1.25 GiB, the size that had already run the full load). Repeat
     starts of the same config then reported identical capacity: B/E 17,106 tokens, C/J 45,056, G/final 32,336.
   - Peak GPU use with the pin: 7,289 MiB (config A, fp8) and 6,322 MiB (final default) of 8,151 MiB, including Windows.
4. **Pinned memory is unavailable under WSL** (`Pinned memory is not available on this platform; falling back to device
   memory for UVA buffers`). NVIDIA documents that pinned system memory is limited in WSL2
   ([CUDA on WSL guide, §4.1](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)). No visible effect here.
5. **Triton JIT during the first requests** (`Triton kernel JIT compilation during inference: _gumbel_sample_kernel`,
   `store_cache_checkpoints_kernel`). This is a one-time latency spike per server start. The single-turn tests ran after
   a warm-up request, so it does not affect them.
6. **`pkill -f "vllm serve"`** inside a `bash -c '... vllm serve ...'` wrapper kills the wrapper itself. Use
   `pkill -f "[v]llm serve"`.
7. **`wsl.exe -- bash -lc '...$var...'`** expands `$var` in the outer login shell first. Use `wsl.exe -e bash -c '...'`.
   A process backgrounded with `&` inside a `wsl.exe` call dies when that call returns.

## 7. Implications for the experiment

- Keep **one fixed server config** for all pilot, assay and swarm runs. Probe P(Yes) moves by about 0.01 (bf16 state or
  block-size changes) up to 0.5 on single prompts (fp8 KV) between configs. Record `scripts/serve_vllm.sh`'s settings
  with each run.
- vLLM batching is not batch-invariant. Identical requests can give slightly different logprobs and greedy text depending
  on what else is in the batch: on the same server, 14 of 24 greedy answers matched exactly when batched, 24 of 24 when
  sent one at a time. Sampling at T=0.7 dominates this for agent behaviour. For the belief probe, either accept it as
  measurement noise or send probes alone.
- Throughput is capacity-bound at 9–21 concurrent sequences. The orchestrator's `LLM_MAX_CONCURRENCY=48` simply queues the
  rest in vLLM. Shorter prompts or outputs raise throughput almost linearly.
- The prefix cache is off, so prompt layout does not affect speed. Turning it on (`PREFIX_CACHE=1`) only makes sense if
  prompts start with an identical prefix of at least one block (≥ 300–1,100 tokens, depending on dtypes). That was not
  tested.

## Artifacts

- Scripts in the repo: [`scripts/setup_vllm.sh`](../scripts/setup_vllm.sh), [`scripts/serve_vllm.sh`](../scripts/serve_vllm.sh).
- Raw logs, on the WSL disk and not in git, under `~/projects/agent-swarm-epi/logs/`:
  - setup: `install_vllm_<ts>.log`, `download_kernels_<ts>.log`. The first install's untimestamped logs were overwritten by
    an idempotent re-run of `setup_vllm.sh` (51 s, no changes). The 12 min 37 s / 8 min 39 s timings in §2 were read from
    them before that.
  - server starts: `vllm_serve_*.log`, `serve_attempt1_maxseqs256_failed.log`, `serve_final.log`
  - sweeps: `sweep2_results.txt` (A–D), `sweep3_results.txt` (E–H), `sweep4_results.txt` (I–J), `sweep5_results.txt`
    (batch-size-1 fidelity)
  - fidelity records: `fid_*.json`, `fidseq_*.json`
  - memory and validation: `mem_*.txt`, `final_windows.txt`, `final_wsl.txt`, and `serving_summary.md` (the tables above)
- Test and analysis scripts: `smoke_test_vllm.py` (smoke, throughput, agent loop, fidelity), `summarize_serving.py` (all
  tables above) and the sweep drivers `sweep_configs.sh`, `sweep3.sh`, `sweep4.sh`, `sweep5_fidelity_seq.sh`. Copies are
  in the shared session notes folder under `serving/`, ready to adopt into `scripts/`. To regenerate the tables:
  `python summarize_serving.py ~/projects/agent-swarm-epi/logs`.

## Sources

- vLLM 0.33.0 release notes (CUDA 13.0-only wheels, PyTorch 2.14, `--mamba-cache-mode` deprecated):
  https://github.com/vllm-project/vllm/releases/tag/v0.33.0rc3 · PyPI: https://pypi.org/project/vllm/0.33.0/
- vLLM GPU installation (uv, `--torch-backend=auto`, `vllm download-kernels`): https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html
- vLLM Qwen3.5 recipe (`--language-model-only`, `--enable-prefix-caching`, `--default-chat-template-kwargs`): https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html
- `vllm serve` CLI reference (all flags above; checked against `vllm serve --help=all` of 0.33.0): https://docs.vllm.ai/en/latest/cli/serve.html
- `vllm bench serve` (alternative standard benchmark, not used for the numbers here): https://docs.vllm.ai/en/latest/cli/bench/serve.html
- Hybrid KV cache manager (one page size across groups; attention block size grown to fit the Mamba state; Mamba state cached at block boundaries): https://docs.vllm.ai/en/latest/design/hybrid_kv_cache_manager.html
- Prefix caching design ("We only cache full blocks"): https://docs.vllm.ai/en/latest/design/prefix_caching.html
- Quantized (fp8) KV cache: https://docs.vllm.ai/en/latest/features/quantization/quantized_kvcache.html
- OpenAI-compatible server extra parameters: https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/
- Qwen3.5-4B model card (architecture, non-thinking sampling, `enable_thinking`): https://huggingface.co/Qwen/Qwen3.5-4B
- Checkpoints: https://huggingface.co/cyankiwi/Qwen3.5-4B-AWQ-4bit · fallback https://huggingface.co/RedHatAI/Qwen3.5-4B-quantized.w4a16
- WSL mirrored networking (localhost works in both directions): https://learn.microsoft.com/en-us/windows/wsl/networking
- CUDA on WSL limitations (pinned memory): https://docs.nvidia.com/cuda/wsl-user-guide/index.html
