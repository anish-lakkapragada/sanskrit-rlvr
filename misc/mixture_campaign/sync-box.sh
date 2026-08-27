#!/bin/bash
# Sync the minimal repo subset a campaign box needs.
#   bash misc/mixture_campaign/sync-box.sh a <ip>
#   bash misc/mixture_campaign/sync-box.sh b <ip>
# Box A gets tb20m + tb15m{100,67,50}; Box B gets tb15m{33,0} + tb10m.
set -eu
BOX=${1:?a|b}
IP=${2:?box ip}
cd "$(dirname "$0")/../.."

COMMON=(
    pyproject.toml uv.lock
    finetune prompts configs
    prevals/__init__.py prevals/eval.py prevals/campaign
    misc/final_translation_eval.py misc/mixture_campaign
    data/finetune/task-data
    data/eval/samayik.json
    data/finetune/sft-standard/samayik_validation.json
    data/finetune/sft-standard/flores-200_validation.json
    data/data-mixture/eval data/data-mixture/manifest.json
    data/data-mixture/val-translation.json data/data-mixture/val-morphology.json
)
if [ "$BOX" = a ]; then
    DATA=(data/data-mixture/tb20m
          data/data-mixture/tb15m/samayik100.json
          data/data-mixture/tb15m/samayik67.json
          data/data-mixture/tb15m/samayik50.json)
else
    DATA=(data/data-mixture/tb15m/samayik33.json
          data/data-mixture/tb15m/samayik0.json
          data/data-mixture/tb10m)
fi

rsync -az --relative \
    -e "ssh -o StrictHostKeyChecking=accept-new" \
    --exclude '__pycache__' \
    "${COMMON[@]}" "${DATA[@]}" "ubuntu@$IP:~/sanskrit/"
echo "[sync-$BOX] done -> $IP"
