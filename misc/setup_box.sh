#!/usr/bin/env bash
# One-shot setup for a fresh Lambda GPU box (run from the Mac):
#   ssh ubuntu@<IP> 'bash -s' < misc/setup_box.sh
# Clones the experiment branch, installs uv, syncs train deps, dry-runs the config.
set -euo pipefail

BRANCH=finetune/vidyut-prakriya
REPO=https://github.com/anish-lakkapragada/sanskrit-rlvr.git
CONFIG=configs/vp-exact-gemma4-26b-1xb200.yml

cd ~
[ -d sanskrit ] || git clone --branch "$BRANCH" "$REPO" sanskrit
cd sanskrit
git pull --ff-only

command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

uv sync --extra train
uv run python -m finetune.grpo --config "$CONFIG" --dry-run --force

nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
echo "SETUP OK"
