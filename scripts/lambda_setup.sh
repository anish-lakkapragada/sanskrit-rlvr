#!/bin/bash
# One-shot setup for a fresh Lambda (or any CUDA Linux) box:
#
#     bash scripts/lambda_setup.sh
#     bash finetune/run.sh finetune/configs/cuda-smoke.yaml   # then verify
#
# Installs uv and the Lean toolchain, builds the checker binaries, and syncs
# the cuda dependency profile. Idempotent — safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v lake >/dev/null && [ ! -x "$HOME/.elan/bin/lake" ]; then
    curl -sSf https://elan.lean-lang.org/elan-init.sh | sh -s -- -y
fi
export PATH="$HOME/.elan/bin:$PATH"

echo "[setup] building the Lean checker (lake build re-proves Tests.lean) …"
(cd lean && lake build)
lean/.lake/build/bin/check --json "gajaḥ vanam gacchati" >/dev/null \
    && echo "[setup] Lean checker OK"

echo "[setup] syncing python env (cuda profile) …"
uv sync --extra cuda

echo "[setup] done — try: bash finetune/run.sh finetune/configs/cuda-smoke.yaml"
