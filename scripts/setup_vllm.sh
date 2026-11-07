#!/usr/bin/env bash
# setup_vllm.sh: one-time install of the vLLM inference server used by the swarm experiments.
#
# Global context: all swarm agents are served by ONE local OpenAI-compatible vLLM server running
# Qwen3.5-4B (4-bit AWQ, thinking off) on an RTX 5070 Laptop GPU (8 GB, Blackwell sm_120) through
# WSL2 Ubuntu 24.04. This script creates an isolated uv venv on the WSL ext4 disk (not /mnt/c, which
# is slow through the 9P bridge), installs a pinned vLLM release, and pre-downloads the model weights.
# Run it INSIDE WSL:  bash scripts/setup_vllm.sh      (serve afterwards with scripts/serve_vllm.sh)
# Versions, numbers and problems/fixes are documented in docs/serving.md.

set -euo pipefail  # stop on the first error, on unset variables, and on failures inside pipes

# Root dir for everything heavy (venv, HF cache, logs) on the WSL ext4 disk; overridable from the environment.
SWARM_ROOT="${SWARM_ROOT:-$HOME/projects/agent-swarm-epi}"
# vLLM release pinned for reproducibility. 0.33.0 (2026-11-02) is the newest PyPI release at setup time;
# Qwen3.5 (`qwen3_5` arch) is supported in releases, so no nightly is needed any more.
# Release notes: https://github.com/vllm-project/vllm/releases (tag v0.33.0rc3 == PyPI 0.33.0)
VLLM_VERSION="${VLLM_VERSION:-0.33.0}"
# Primary 4-bit checkpoint (compressed-tensors AWQ, group 32, Apache-2.0): https://huggingface.co/cyankiwi/Qwen3.5-4B-AWQ-4bit
MODEL="${MODEL:-cyankiwi/Qwen3.5-4B-AWQ-4bit}"
# uv binary (installed per https://docs.astral.sh/uv/getting-started/installation/); falls back to PATH lookup.
UV="${UV:-$(command -v uv || echo "$HOME/.local/bin/uv")}"

mkdir -p "$SWARM_ROOT/hf-cache" "$SWARM_ROOT/logs"  # HF cache + logs live next to the venv on ext4
cd "$SWARM_ROOT"                                      # all relative paths below resolve inside SWARM_ROOT
TS="$(date +%Y%m%dT%H%M%S)"                           # timestamp, so a re-run never overwrites the first install's logs

# Create the venv with Python 3.12 (vLLM 0.33 supports 3.11-3.14 per its PyPI metadata `requires_python`).
# `--seed` installs pip into the venv so tools that shell out to pip still work.
# Source: https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html ("uv venv --python 3.12 --seed")
[ -d vllm-env ] || "$UV" venv vllm-env --python 3.12 --seed

# Activate the venv so `uv pip` targets it and `vllm` lands on PATH.
source vllm-env/bin/activate

# Install vLLM. `--torch-backend=auto` makes uv pick the PyTorch wheel matching the installed driver's CUDA.
# vLLM 0.33.0 wheels are CUDA 13.0 only (release notes: "CUDA 12.9 dropped") and pin torch==2.14.0;
# the Windows driver 617.42 exposes CUDA 13.4 to WSL, which satisfies CUDA 13.0. torch>=2.7 cu128+ wheels
# include sm_120 (Blackwell consumer) kernels, so no source build / nvcc is needed.
# Source: https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html ("uv pip install vllm --torch-backend=auto")
"$UV" pip install "vllm==${VLLM_VERSION}" --torch-backend=auto 2>&1 | tee "logs/install_vllm_${TS}.log"

# Pre-download FlashInfer's precompiled kernels; without them they are JIT-compiled at first start,
# "which can add several minutes on Hopper and newer GPUs, especially Blackwell". Non-fatal if it fails.
# Source: https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html (`vllm download-kernels`)
vllm download-kernels 2>&1 | tee "logs/download_kernels_${TS}.log" || echo "WARN: vllm download-kernels failed; kernels will JIT at start"

# Keep the HF cache on the WSL disk so the 4 GB checkpoint is read from ext4, not /mnt/c.
# Source: https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables#hfhome
export HF_HOME="$SWARM_ROOT/hf-cache"

# Pre-download the checkpoint (uses hf_xet for fast chunked transfer). `hf` ships with huggingface_hub,
# a vLLM dependency. Source: https://huggingface.co/docs/huggingface_hub/guides/cli#hf-download
hf download "$MODEL" 2>&1 | tail -n 3

# Print the installed stack so it can be pasted into docs/serving.md.
python -c "import vllm, torch, transformers; print('vllm', vllm.__version__, '| torch', torch.__version__, '| cuda', torch.version.cuda, '| transformers', transformers.__version__, '| gpu', torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0))"
