#!/bin/bash
set -euo pipefail
TASK_ROOT=/lambda/nfs/sanskrit-serve/grpo-r3-full-20260920
SHARD="$1"
export HF_HOME=/lambda/nfs/sanskrit-serve/hf-cache
export VLLM_ATTENTION_BACKEND=FLASH_ATTN
export VLLM_USE_FLASHINFER_SAMPLER=0
export TOKENIZERS_PARALLELISM=false
cd "$TASK_ROOT/repo"
for attempt in $(seq 1 240); do
    if [ -f "$TASK_ROOT/model-ready.json" ]; then break; fi
    sleep 15
done
test -f "$TASK_ROOT/model-ready.json"
exec "$TASK_ROOT/env/bin/python" -u -m misc.benchmark_full_eval run \
    --tasks "$TASK_ROOT/tasks-$SHARD.json" \
    --output "$TASK_ROOT/results/samples-$SHARD.jsonl" \
    --model "$TASK_ROOT/grpo-r3-final-merged" --batch-tasks 64
