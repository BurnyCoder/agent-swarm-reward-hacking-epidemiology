#!/usr/bin/env bash
# serve_vllm.sh: start the OpenAI-compatible vLLM server that every swarm agent talks to.
#
# Global context: the orchestrator (src/swarm_epi/config.py) sends chat completions to
# LLM_BASE_URL=http://localhost:8000/v1 with model name "cyankiwi/Qwen3.5-4B-AWQ-4bit" and thinking off.
# WSL2 runs with networkingMode=mirrored, so the server is reachable from Windows at localhost:8000 too.
# Run INSIDE WSL after scripts/setup_vllm.sh:  bash scripts/serve_vllm.sh   (extra args are appended to `vllm serve`)
# Defaults were chosen by the measured sweep in docs/serving.md (throughput + fidelity); each is an env switch.

set -euo pipefail  # fail fast on errors / unset variables / broken pipes

SWARM_ROOT="${SWARM_ROOT:-$HOME/projects/agent-swarm-epi}"  # venv + HF cache + logs on the WSL ext4 disk (see setup_vllm.sh)
MODEL="${MODEL:-cyankiwi/Qwen3.5-4B-AWQ-4bit}"               # fallback: MODEL=RedHatAI/Qwen3.5-4B-quantized.w4a16
PORT="${PORT:-8000}"                                         # must match LLM_BASE_URL in .env
GPU_UTIL="${GPU_UTIL:-0.8}"                                  # fraction of the 8 GB GPU vLLM may claim; only sizes the KV cache if KV_CACHE_BYTES=""
KV_CACHE_BYTES="${KV_CACHE_BYTES-1342177280}"                # pinned KV-cache size = 1.25 GiB (see below); set KV_CACHE_BYTES="" to size from GPU_UTIL
KV_DTYPE="${KV_DTYPE:-auto}"                                 # attention KV dtype: auto = model dtype (bf16); KV_DTYPE=fp8 is faster but lossy (see below)
SSM_DTYPE="${SSM_DTYPE:-bfloat16}"                           # Gated-DeltaNet recurrent-state dtype; SSM_DTYPE=auto = config's float32 (model-native)
PREFIX_CACHE="${PREFIX_CACHE:-0}"                            # 1 = --enable-prefix-caching; off by default (0% hits on the swarm workload, see below)
MAX_NUM_SEQS="${MAX_NUM_SEQS:-64}"                           # max sequences per engine step; vLLM default 256 does not fit (see below)

source "$SWARM_ROOT/vllm-env/bin/activate"   # venv created by setup_vllm.sh (puts `vllm` on PATH)
export HF_HOME="$SWARM_ROOT/hf-cache"        # read the pre-downloaded checkpoint from ext4 (https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables#hfhome)
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}" # no network lookups at start: weights are already cached, so restarts are reproducible and fast
mkdir -p "$SWARM_ROOT/logs"                  # server logs go next to the venv
LOG="$SWARM_ROOT/logs/vllm_serve_$(date +%Y%m%dT%H%M%S).log"  # one timestamped log per server start

# Engine/server flags (all documented at https://docs.vllm.ai/en/latest/cli/serve.html):
#   --language-model-only        skip the Qwen3.5 vision encoder and multimodal profiling to free memory for KV cache
#                                (Qwen3.5-4B model card "text-only" command: https://huggingface.co/Qwen/Qwen3.5-4B)
#   --max-model-len 4096         longest prompt+output per request; swarm prompts are ~2k tokens + <=400 output
#   --gpu-memory-utilization     cap on GPU memory for this process (the Windows desktop holds 0.8-1.7 GiB of the 8 GB)
#   --kv-cache-dtype auto        bf16 attention KV. fp8 (e4m3, unscaled: the checkpoint ships no KV scales,
#                                https://docs.vllm.ai/en/latest/features/quantization/quantized_kvcache.html) fits ~1.6x more
#                                requests but moved the Yes/No probe by up to 0.57 and flipped 2/24 answers (docs/serving.md)
#   --mamba-ssm-cache-dtype      bf16 Gated-DeltaNet state halves the 48 MiB/sequence fp32 state: +19% single-turn and +9%
#                                swarm-loop throughput; probe shift vs fp32 mean 0.011 / max 0.060, no flips (docs/serving.md)
#   --no-enable-prefix-caching   the hybrid model's prefix cache ("align" mode) only hits whole 300-1000-token blocks, gave 0%
#                                hits on the swarm-shaped 4-call loop, cost 1-17% throughput, and with bf16 state produced one
#                                0.47 probe outlier; the vLLM Qwen3.5 recipe enables it for shared-prefix workloads
#                                (https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html)
#   --default-chat-template-kwargs  server-side default enable_thinking=false, so a request that forgets extra_body still
#                                gets non-thinking output; per-request chat_template_kwargs override it (recipe page above)
#   --max-num-seqs 64            with the default 256 vLLM 0.33 refuses to start: "max_num_seqs (256) exceeds available
#                                Mamba cache blocks (93)" (each decoding sequence needs one Gated-DeltaNet state block),
#                                and 256 also wastes memory on sampler buffers and 51 CUDA-graph sizes (188 s capture)
#   --kv-cache-memory-bytes      pin the KV cache (attention KV + Gated-DeltaNet state blocks) to a fixed size. Under WSL the
#                                startup profiler also counts GPU memory that Windows apps allocate meanwhile, so sizing from
#                                --gpu-memory-utilization gave 1.25 GiB on one start and 0.79 GiB on the next (docs/serving.md);
#                                a fixed size makes capacity and throughput reproducible. Overrides GPU_UTIL for KV sizing.
#   --port                       OpenAI-compatible HTTP port (/v1/chat/completions, /v1/models, /metrics)
KV_ARGS=()                                                       # empty array -> no flag, vLLM sizes KV from GPU_UTIL
[ -n "$KV_CACHE_BYTES" ] && KV_ARGS=(--kv-cache-memory-bytes "$KV_CACHE_BYTES")
PC_FLAG=--no-enable-prefix-caching                               # BooleanOptionalAction pair in vLLM's CLI
[ "$PREFIX_CACHE" = 1 ] && PC_FLAG=--enable-prefix-caching
# stdbuf -oL + tee: stream the log to the terminal line by line and keep a timestamped copy.
stdbuf -oL vllm serve "$MODEL" \
  --language-model-only \
  --max-model-len 4096 \
  --gpu-memory-utilization "$GPU_UTIL" \
  --kv-cache-dtype "$KV_DTYPE" \
  --mamba-ssm-cache-dtype "$SSM_DTYPE" \
  "$PC_FLAG" \
  --max-num-seqs "$MAX_NUM_SEQS" \
  "${KV_ARGS[@]}" \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --port "$PORT" \
  "$@" 2>&1 | tee "$LOG"
