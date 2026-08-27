#!/bin/bash
# One-time box setup for the data-mixture campaign (run on the Lambda box).
# Installs uv, syncs the training env, prefetches the base model so the 8
# concurrent pipelines don't race on the download.
set -eu
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/sanskrit"
uv sync --extra train
uv run python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3-4B')"
nvidia-smi -L
echo "[setup] done"
