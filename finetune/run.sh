#!/bin/bash
# Launch a fine-tuning experiment from a YAML config:
#
#     bash finetune/run.sh finetune/configs/sft-baseline.yaml [--force]
#
# Runs offline (models must already be in the HF cache) and from the repo
# root, whatever directory you call it from.
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_HUB_OFFLINE=1 HF_HUB_DISABLE_XET=1
exec .venv/bin/python -m finetune.train "$@"
