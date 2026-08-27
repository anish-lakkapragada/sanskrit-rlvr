#!/bin/bash
# GRPO round-3 box setup: train env + the driver-570 CUDA stack fix
# (cu128 torch/vision/audio + vllm cu129 --no-deps + import smoke test).
set -eu
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/sanskrit"
uv sync --extra train
uv pip install --index-url https://download.pytorch.org/whl/cu128 \
    "torch==2.11.0+cu128" "torchvision==0.26.0+cu128" "torchaudio==2.11.0+cu128"
uv pip install --no-deps \
    "vllm @ https://github.com/vllm-project/vllm/releases/download/v0.25.1/vllm-0.25.1%2Bcu129-cp38-abi3-manylinux_2_28_x86_64.whl"
uv run --no-sync python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3-4B')"
uv run --no-sync python -c "
import torch
from transformers import TrainingArguments
from trl import GRPOConfig, GRPOTrainer
print('[setup] stack OK | torch', torch.__version__, '| cuda', torch.cuda.is_available())"
nvidia-smi -L
echo "[setup] done"
