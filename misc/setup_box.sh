#!/usr/bin/env bash
# One-shot setup for a fresh Lambda GPU box (run from the Mac):
#   ssh ubuntu@<IP> 'bash -s' < misc/setup_box.sh
# Clones the experiment branch, installs uv, syncs train deps, dry-runs the config.
set -euo pipefail

BRANCH=finetune/vidyut-prakriya
REPO=https://github.com/anish-lakkapragada/sanskrit-rlvr.git
CONFIG=${1:-configs/vp-exact-gemma3-12b-1xa100.yml}

cd ~
[ -d sanskrit ] || git clone --branch "$BRANCH" "$REPO" sanskrit
cd sanskrit
git pull --ff-only

command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Lambda's stock image ships driver 570 (CUDA 12.8); torch 2.11 wheels are
# CUDA 13. The forward-compat package bridges it (datacenter GPUs only) —
# every python invocation needs LD_LIBRARY_PATH=/usr/local/cuda-13.0/compat.
if [ ! -d /usr/local/cuda-13.0/compat ]; then
  wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb -O /tmp/ck.deb
  sudo dpkg -i /tmp/ck.deb >/dev/null
  sudo apt-get update -qq >/dev/null 2>&1 || true
  sudo apt-get install -y -qq cuda-compat-13-0
fi
export LD_LIBRARY_PATH=/usr/local/cuda-13.0/compat:${LD_LIBRARY_PATH:-}
# Colocated vLLM + training on one card fragments the allocator badly
# (~2.6GB reserved-but-unallocated was enough to OOM the backward pass).
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

uv sync --extra train
uv run python -m finetune.grpo --config "$CONFIG" --dry-run --force

nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
echo "SETUP OK"
