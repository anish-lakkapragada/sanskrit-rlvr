#!/usr/bin/env bash
# One-shot setup for a fresh Lambda GPU box (run from the Mac):
#   ssh ubuntu@<IP> 'bash -s' < misc/setup_box.sh [config-path]
# Clones the experiment branch, installs uv, syncs train deps, works out
# whether the CUDA forward-compat shim is needed, and dry-runs the config.
#
# Writes ~/sanskrit/.gpu_env with the environment the trainer needs; the
# launcher sources it rather than hard-coding LD_LIBRARY_PATH, because
# forcing the compat libs on a box whose driver is already new breaks CUDA.
set -euo pipefail

BRANCH=finetune/vidyut-prakriya
REPO=https://github.com/anish-lakkapragada/sanskrit-rlvr.git
CONFIG=${1:-configs/vp-exact-gemma4-26b-1xb200.yml}

cd ~
[ -d sanskrit ] || git clone --branch "$BRANCH" "$REPO" sanskrit
cd sanskrit
git fetch -q origin "$BRANCH" && git reset -q --hard "origin/$BRANCH"

command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv sync --extra train

# Colocated vLLM + training on one card fragments the allocator badly
# (2.6GB reserved-but-unallocated was enough to OOM a backward pass).
GPU_ENV="export PATH=\$HOME/.local/bin:\$PATH
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"

cuda_ok() { .venv/bin/python -c "import torch; assert torch.cuda.is_available(); torch.randn(8, device='cuda')" 2>/dev/null; }

if cuda_ok; then
  echo "[setup] CUDA works against the stock driver"
else
  echo "[setup] stock driver too old for these wheels; installing forward-compat"
  wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb -O /tmp/ck.deb
  sudo dpkg -i /tmp/ck.deb >/dev/null
  sudo apt-get update -qq >/dev/null 2>&1 || true
  sudo apt-get install -y -qq cuda-compat-13-0
  export LD_LIBRARY_PATH=/usr/local/cuda-13.0/compat:${LD_LIBRARY_PATH:-}
  cuda_ok || { echo "[setup] FATAL: CUDA still unavailable with compat libs"; exit 1; }
  echo "[setup] CUDA works via /usr/local/cuda-13.0/compat"
  GPU_ENV="$GPU_ENV
export LD_LIBRARY_PATH=/usr/local/cuda-13.0/compat:\${LD_LIBRARY_PATH:-}"
fi

printf '%s\n' "$GPU_ENV" > ~/sanskrit/.gpu_env
# shellcheck disable=SC1090
source ~/sanskrit/.gpu_env

uv run python -m finetune.grpo --config "$CONFIG" --dry-run --force
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
echo "SETUP OK"
