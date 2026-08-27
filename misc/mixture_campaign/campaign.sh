#!/bin/bash
# Data-mixture campaign orchestrator: one train->chrF->VP pipeline per GPU.
#   bash campaign.sh a   (Box A: tb20m x5 + tb15m {100,67,50})
#   bash campaign.sh b   (Box B: tb15m {33,0} + tb10m x5 + base evals on GPU 7)
# Each GPU runs its arm's full pipeline sequentially; GPUs are independent.
# Progress: logs/<name>.{train,chrf,vp}.log, logs/<name>.DONE / .FAILED,
# logs/ALL-DONE when every pipeline on the box has finished.
set -u
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/sanskrit"
mkdir -p logs

CFG_DIR=configs/sft-data-mixture

case "${1:?usage: campaign.sh a|b}" in
a) ARMS=(
    "0:$CFG_DIR/token-budget-20m/mixture-samayik-100.yml:sft-qwen3-4b-tb20m-samayik100"
    "1:$CFG_DIR/token-budget-20m/mixture-samayik-67.yml:sft-qwen3-4b-tb20m-samayik67"
    "2:$CFG_DIR/token-budget-20m/mixture-samayik-50.yml:sft-qwen3-4b-tb20m-samayik50"
    "3:$CFG_DIR/token-budget-20m/mixture-samayik-33.yml:sft-qwen3-4b-tb20m-samayik33"
    "4:$CFG_DIR/token-budget-20m/mixture-samayik-0.yml:sft-qwen3-4b-tb20m-samayik0"
    "5:$CFG_DIR/token-budget-15m/mixture-samayik-100.yml:sft-qwen3-4b-tb15m-samayik100"
    "6:$CFG_DIR/token-budget-15m/mixture-samayik-67.yml:sft-qwen3-4b-tb15m-samayik67"
    "7:$CFG_DIR/token-budget-15m/mixture-samayik-50.yml:sft-qwen3-4b-tb15m-samayik50"
  ) ;;
b) ARMS=(
    "0:$CFG_DIR/token-budget-15m/mixture-samayik-33.yml:sft-qwen3-4b-tb15m-samayik33"
    "1:$CFG_DIR/token-budget-15m/mixture-samayik-0.yml:sft-qwen3-4b-tb15m-samayik0"
    "2:$CFG_DIR/token-budget-10m/mixture-samayik-100.yml:sft-qwen3-4b-tb10m-samayik100"
    "3:$CFG_DIR/token-budget-10m/mixture-samayik-67.yml:sft-qwen3-4b-tb10m-samayik67"
    "4:$CFG_DIR/token-budget-10m/mixture-samayik-50.yml:sft-qwen3-4b-tb10m-samayik50"
    "5:$CFG_DIR/token-budget-10m/mixture-samayik-33.yml:sft-qwen3-4b-tb10m-samayik33"
    "6:$CFG_DIR/token-budget-10m/mixture-samayik-0.yml:sft-qwen3-4b-tb10m-samayik0"
  ) ;;
*) echo "unknown box: $1" >&2; exit 1 ;;
esac

pipeline() {
    local gpu=$1 cfg=$2 name=$3
    if CUDA_VISIBLE_DEVICES=$gpu uv run --no-sync python -m finetune.sft --config "$cfg" --force \
            > "logs/$name.train.log" 2>&1 \
       && CUDA_VISIBLE_DEVICES=$gpu uv run --no-sync python misc/final_translation_eval.py \
            --model Qwen/Qwen3-4B --adapter "runs/$name/adapter" \
            --out-dir "runs/$name/evals-final" > "logs/$name.chrf.log" 2>&1 \
       && CUDA_VISIBLE_DEVICES=$gpu uv run --no-sync python -m prevals.eval \
            "prevals/campaign/eval-$name.yml" > "logs/$name.vp.log" 2>&1; then
        touch "logs/$name.DONE"
    else
        touch "logs/$name.FAILED"
    fi
}

base_pipeline() {  # Box B GPU 7: the two axis-origin evals, no training
    if CUDA_VISIBLE_DEVICES=7 uv run --no-sync python misc/final_translation_eval.py \
            --model Qwen/Qwen3-4B --out-dir runs/base-qwen3-4b/evals-final \
            > logs/base.chrf.log 2>&1 \
       && CUDA_VISIBLE_DEVICES=7 uv run --no-sync python -m prevals.eval \
            prevals/campaign/eval-base.yml > logs/base.vp.log 2>&1; then
        touch logs/base.DONE
    else
        touch logs/base.FAILED
    fi
}

for spec in "${ARMS[@]}"; do
    IFS=: read -r gpu cfg name <<< "$spec"
    pipeline "$gpu" "$cfg" "$name" &
    sleep 3   # stagger startup (tokenization + cache warm)
done
[ "$1" = b ] && base_pipeline &

wait
touch logs/ALL-DONE
echo "[campaign $1] all pipelines finished"
