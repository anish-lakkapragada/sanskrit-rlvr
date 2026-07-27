#!/usr/bin/env bash
# Start the 8x A100 80GB run ON THE BOX: vllm-serve on GPU 7, DDP training on
# GPUs 0-6, TensorBoard on 127.0.0.1:6006. Idempotent -- kills prior sessions.
#   ssh ubuntu@<IP> 'bash -s' < misc/launch_8xa100.sh
set -euo pipefail

CONFIG=${1:-configs/vp-exact-gemma4-26b-8xa100-80gb.yml}
MODEL=google/gemma-4-26B-A4B-it
TRAIN_GPUS=0,1,2,3,4,5,6
VLLM_GPU=7
NPROC=7
PORT=8000

cd ~/sanskrit
source ~/sanskrit/.gpu_env

for s in train vllm tb; do tmux kill-session -t "$s" 2>/dev/null || true; done

# ---- 1. rollout server on GPU 7 -------------------------------------------
# max_model_len must match the config: gemma4 advertises 262k and vLLM sizes
# its KV cache to serve one request at that length, which will not fit.
tmux new-session -d -s vllm "cd ~/sanskrit && source ~/sanskrit/.gpu_env && \
  CUDA_VISIBLE_DEVICES=$VLLM_GPU uv run trl vllm-serve \
    --model $MODEL --port $PORT --dtype bfloat16 \
    --max_model_len 2048 --gpu_memory_utilization 0.9 2>&1 | tee vllm.log"

echo "[launch] waiting for vllm-serve to load ~53GB (this takes several minutes)"
for i in $(seq 1 90); do
  if curl -sf "http://127.0.0.1:$PORT/health/" >/dev/null 2>&1; then
    echo "[launch] vLLM server healthy after ${i}0s"; break
  fi
  if ! tmux has-session -t vllm 2>/dev/null; then
    echo "[launch] FATAL: vllm-serve died. Last lines:"; tail -30 vllm.log; exit 1
  fi
  sleep 10
done
curl -sf "http://127.0.0.1:$PORT/health/" >/dev/null 2>&1 || {
  echo "[launch] FATAL: server never became healthy"; tail -30 vllm.log; exit 1; }

# ---- 2. TensorBoard (tunnel to it from the Mac) ----------------------------
mkdir -p runs
tmux new-session -d -s tb "cd ~/sanskrit && source ~/sanskrit/.gpu_env && \
  uv run tensorboard --logdir runs --host 127.0.0.1 --port 6006 2>&1 | tee tb.log"

# ---- 3. DDP training on GPUs 0-6 ------------------------------------------
tmux new-session -d -s train "cd ~/sanskrit && source ~/sanskrit/.gpu_env && \
  CUDA_VISIBLE_DEVICES=$TRAIN_GPUS uv run accelerate launch \
    --num_processes $NPROC --mixed_precision bf16 \
    -m finetune.grpo --config $CONFIG --force 2>&1 | tee train.log"

sleep 10
for s in vllm tb train; do
  tmux has-session -t "$s" 2>/dev/null && echo "$s session: LIVE" || echo "$s session: DEAD"
done
nvidia-smi --query-gpu=index,memory.used --format=csv,noheader
echo "LAUNCH OK"
