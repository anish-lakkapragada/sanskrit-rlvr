#!/bin/bash
# Conjugate-prompt (drill-costume) run: 5 boxes, one template, <answer> extraction.
# Same pipeline as orchestrate_local.sh; outputs -> evals-conjprompt/.
set -u
cd "$(dirname "$0")/../.."
source .env
KEY="${LAMBDA_API_KEY:-$LAMBDA_CLOUD_API_KEY}"
LOGS=runs-final/elicitation-logs
mkdir -p "$LOGS"
SSH="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15"
TPL="prompts/v1/translation-conjprompt/translation_drill_costume.txt"
OUTNAME="samayik-drill-costume.json"

ip_of() {
    curl -su "$KEY:" https://cloud.lambdalabs.com/api/v1/instances | python3 -c "
import json, sys
for i in json.load(sys.stdin)['data']:
    if i['name'] == '$1' and i['status'] == 'active' and i.get('ip'):
        print(i['id'], i['ip'])"
}

retry_rsync() {
    for wait in 20 40 60 90 120 120; do
        rsync -az -e "$SSH" "$@" && return 0
        echo "  rsync failed; retrying in ${wait}s"; sleep "$wait"
    done
    return 1
}

run_box() {  # $1=name $2=mode $3=adapter_dir $4=out_local_dir [$5=extra_adapter]
    local name="$1" mode="$2" adapter="$3" out_local="$4" extra="${5:-}"
    local id="" ip=""
    for _ in $(seq 1 60); do
        read -r id ip <<<"$(ip_of "$name")" || true
        [ -n "${ip:-}" ] && break
        sleep 15
    done
    [ -z "${ip:-}" ] && { echo "[$name] never became active"; return 1; }
    echo "[$name] active at $ip (id $id)"
    sleep 45

    retry_rsync pyproject.toml uv.lock README.md "ubuntu@$ip:~/sanskrit/" || return 1
    retry_rsync -r finetune misc prompts "ubuntu@$ip:~/sanskrit/" || return 1
    retry_rsync -R data/data-mixture/eval/samayik-eval.json "ubuntu@$ip:~/sanskrit/" || return 1
    retry_rsync -r "$adapter/" "ubuntu@$ip:~/sanskrit/adapter-main/" || return 1
    if [ -n "$extra" ]; then
        retry_rsync -r "$extra/" "ubuntu@$ip:~/sanskrit/adapter-sft/" || return 1
    fi
    echo "[$name] payload synced"

    $SSH "ubuntu@$ip" "nohup bash -c 'sleep 10800; curl -su ${KEY}: -X POST \
        https://cloud.lambdalabs.com/api/v1/instance-operations/terminate \
        -H \"Content-Type: application/json\" \
        -d \"{\\\"instance_ids\\\":[\\\"$id\\\"]}\"' >/dev/null 2>&1 &"
    echo "[$name] 3h backstop armed"

    $SSH "ubuntu@$ip" "cd ~/sanskrit && bash misc/grpo_r3/setup-box.sh" || return 1
    echo "[$name] env ready; generating"
    $SSH "ubuntu@$ip" "cd ~/sanskrit && bash misc/elicitation/run_box.sh $mode $TPL $OUTNAME answer" || return 1

    mkdir -p "$out_local"
    retry_rsync "ubuntu@$ip:~/sanskrit/out-elicitation/*.json" "$out_local/" || return 1
    echo "[$name] PULLED -> $out_local"
    echo "[$name] ALL-DONE"
}

run_box conj-s100 sft runs-final/sft-qwen3-4b-tb20m-samayik100/adapter \
    runs-final/sft-qwen3-4b-tb20m-samayik100/evals-conjprompt \
    > "$LOGS/conj-s100.log" 2>&1 &
run_box conj-s67 sft runs-final/sft-qwen3-4b-tb20m-samayik67/adapter \
    runs-final/sft-qwen3-4b-tb20m-samayik67/evals-conjprompt \
    > "$LOGS/conj-s67.log" 2>&1 &
run_box conj-s50 sft runs-final/sft-qwen3-4b-tb20m-samayik50/adapter \
    runs-final/sft-qwen3-4b-tb20m-samayik50/evals-conjprompt \
    > "$LOGS/conj-s50.log" 2>&1 &
run_box conj-s33 sft runs-final/sft-qwen3-4b-tb20m-samayik33/adapter \
    runs-final/sft-qwen3-4b-tb20m-samayik33/evals-conjprompt \
    > "$LOGS/conj-s33.log" 2>&1 &
run_box conj-grpo grpo runs-final/grpo-r3-final/adapter \
    runs-final/grpo-r3-finals-results/finals/final731-conjprompt \
    runs-final/sft-qwen3-4b-tb20m-samayik67/adapter \
    > "$LOGS/conj-grpo.log" 2>&1 &

wait
echo "ORCHESTRATOR-DONE: $(grep -l 'ALL-DONE' $LOGS/conj-*.log 2>/dev/null | wc -l)/5 boxes finished"
