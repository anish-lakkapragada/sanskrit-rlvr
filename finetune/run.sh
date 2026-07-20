#!/bin/bash
# Launch a fine-tuning experiment from a YAML config:
#
#     bash finetune/run.sh finetune/configs/sft-baseline.yaml [--force]
#
# Reads the config's `backend:` line to sync the matching uv extra
# (mlx → mlx-lm-lora, cuda → TRL + vLLM), then runs from the repo root,
# whatever directory you call it from.
set -euo pipefail
cd "$(dirname "$0")/.."
backend=$(awk '$1 == "backend:" {print $2; exit}' "$1")
export HF_HUB_DISABLE_XET=1  # Xet downloads stall on some networks
if [ "$backend" = "mlx" ]; then
    export HF_HUB_OFFLINE=1  # local workflow: models are pre-cached
fi
exec uv run --extra "${backend:-mlx}" python -m finetune.train "$@"
