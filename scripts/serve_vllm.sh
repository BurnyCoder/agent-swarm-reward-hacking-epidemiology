#!/usr/bin/env bash
# serve_vllm.sh: start the OpenAI-compatible vLLM server that every swarm agent talks to.
#
# Global context: the orchestrator (src/swarm_epi/config.py) sends chat completions to
# LLM_BASE_URL=http://localhost:8000/v1 with model name "cyankiwi/Qwen3.5-4B-AWQ-4bit" and thinking off.
# WSL2 runs with networkingMode=mirrored, so the server is reachable from Windows at localhost:8000 too.
# Run INSIDE WSL after scripts/setup_vllm.sh:  bash scripts/serve_vllm.sh   (extra args are appended to `vllm serve`)
# Flag choices, measured max concurrency and throughput are documented in docs/serving.md.

set -euo pipefail  # fail fast on errors / unset variables / broken pipes

SWARM_ROOT="${SWARM_ROOT:-$HOME/projects/agent-swarm-epi}"  # venv + HF cache + logs on the WSL ext4 disk (see setup_vllm.sh)
MODEL="${MODEL:-cyankiwi/Qwen3.5-4B-AWQ-4bit}"               # fallback: MODEL=RedHatAI/Qwen3.5-4B-quantized.w4a16
PORT="${PORT:-8000}"                                         # must match LLM_BASE_URL in .env
GPU_UTIL="${GPU_UTIL:-0.8}"                                  # fraction of the 8 GB GPU vLLM may claim (weights + activations + KV cache)
KV_DTYPE="${KV_DTYPE:-fp8}"                                  # KV cache dtype; set KV_DTYPE=auto to use the model dtype (bf16)

source "$SWARM_ROOT/vllm-env/bin/activate"   # venv created by setup_vllm.sh (puts `vllm` on PATH)
export HF_HOME="$SWARM_ROOT/hf-cache"        # read the pre-downloaded checkpoint from ext4 (https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables#hfhome)
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}" # no network lookups at start: weights are already cached, so restarts are reproducible and fast
mkdir -p "$SWARM_ROOT/logs"                  # server logs go next to the venv
LOG="$SWARM_ROOT/logs/vllm_serve_$(date +%Y%m%dT%H%M%S).log"  # one timestamped log per server start

# Engine/server flags (all documented at https://docs.vllm.ai/en/latest/cli/serve.html):
#   --language-model-only        skip the Qwen3.5 vision encoder and multimodal profiling to free memory for KV cache
#                                (Qwen3.5-4B model card "text-only" command: https://huggingface.co/Qwen/Qwen3.5-4B)
#   --max-model-len 4096         longest prompt+output per request; swarm prompts are ~2k tokens + <=400 output
#   --gpu-memory-utilization     cap on total GPU memory for this process (the Windows desktop already holds ~1.7 GB)
#   --enable-prefix-caching      reuse KV for shared prompt prefixes (system prompt, task text); the vLLM Qwen3.5 recipe
#                                uses it for throughput (https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html)
#   --kv-cache-dtype fp8         store attention KV in FP8 (e4m3) to roughly double KV capacity
#                                (https://docs.vllm.ai/en/latest/features/quantization/quantized_kvcache.html)
#   --default-chat-template-kwargs  server-side default enable_thinking=false, so a request that forgets extra_body still
#                                gets non-thinking output; per-request chat_template_kwargs override it (recipe page above)
#   --port                       OpenAI-compatible HTTP port (/v1/chat/completions, /v1/models, /metrics)
# stdbuf -oL + tee: stream the log to the terminal line by line and keep a timestamped copy.
stdbuf -oL vllm serve "$MODEL" \
  --language-model-only \
  --max-model-len 4096 \
  --gpu-memory-utilization "$GPU_UTIL" \
  --enable-prefix-caching \
  --kv-cache-dtype "$KV_DTYPE" \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --port "$PORT" \
  "$@" 2>&1 | tee "$LOG"
