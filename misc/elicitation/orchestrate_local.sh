#!/bin/bash
# Local orchestrator for the 5 elicitation boxes. One background pipeline per
# box: wait-active -> payload rsync (retry) -> arm 3h self-terminate backstop ->
# setup-box.sh -> run_box.sh -> pull outputs to the local per-model dirs.
# Boxes are NOT terminated here; the driver session verifies outputs first and
# terminates explicitly (backstop covers a dead laptop).
set -u
cd "$(dirname "$0")/../.."
source .env
KEY="${LAMBDA_API_KEY:-$LAMBDA_CLOUD_API_KEY}"
LOGS=runs-final/elicitation-logs
mkdir -p "$LOGS"
SSH="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15"

ip_of() {  # $1 = instance name
    curl -su "$KEY:" https://cloud.lambdalabs.com/api/v1/instances | python3 -c "
import json, sys
for i in json.load(sys.stdin)['data']:
    if i['name'] == '$1' and i['status'] == 'active' and i.get('ip'):
        print(i['id'], i['ip'])"
}

retry_rsync() {  # retry with backoff (lambda sshd flaps during cloud-init)
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
    sleep 45  # let cloud-init settle past the fake-ready sshd window

    retry_rsync pyproject.toml uv.lock README.md "ubuntu@$ip:~/sanskrit/" || return 1
    retry_rsync -r finetune misc prompts "ubuntu@$ip:~/sanskrit/" || return 1
    retry_rsync -R data/data-mixture/eval/samayik-eval.json "ubuntu@$ip:~/sanskrit/" || return 1
    retry_rsync -r "$adapter/" "ubuntu@$ip:~/sanskrit/adapter-main/" || return 1
    if [ -n "$extra" ]; then
        retry_rsync -r "$extra/" "ubuntu@$ip:~/sanskrit/adapter-sft/" || return 1
    fi
    echo "[$name] payload synced"

    # 3h self-terminate backstop (survives a dead laptop)
    $SSH "ubuntu@$ip" "nohup bash -c 'sleep 10800; curl -su ${KEY}: -X POST \
        https://cloud.lambdalabs.com/api/v1/instance-operations/terminate \
        -H \"Content-Type: application/json\" \
        -d \"{\\\"instance_ids\\\":[\\\"$id\\\"]}\"' >/dev/null 2>&1 &"
    echo "[$name] 3h backstop armed"

    $SSH "ubuntu@$ip" "cd ~/sanskrit && bash misc/grpo_r3/setup-box.sh" || return 1
    echo "[$name] env ready; generating"
    $SSH "ubuntu@$ip" "cd ~/sanskrit && bash misc/elicitation/run_box.sh $mode" || return 1

    mkdir -p "$out_local"
    retry_rsync "ubuntu@$ip:~/sanskrit/out-elicitation/*.json" "$out_local/" || return 1
    echo "[$name] PULLED -> $out_local"
    echo "$id" > "$LOGS/$name.instance-id"
    echo "[$name] ALL-DONE"
}

run_box elic-s100 sft runs-final/sft-qwen3-4b-tb20m-samayik100/adapter \
    runs-final/sft-qwen3-4b-tb20m-samayik100/evals-elicitation \
    > "$LOGS/elic-s100.log" 2>&1 &
run_box elic-s67 sft runs-final/sft-qwen3-4b-tb20m-samayik67/adapter \
    runs-final/sft-qwen3-4b-tb20m-samayik67/evals-elicitation \
    > "$LOGS/elic-s67.log" 2>&1 &
run_box elic-s50 sft runs-final/sft-qwen3-4b-tb20m-samayik50/adapter \
    runs-final/sft-qwen3-4b-tb20m-samayik50/evals-elicitation \
    > "$LOGS/elic-s50.log" 2>&1 &
run_box elic-s33 sft runs-final/sft-qwen3-4b-tb20m-samayik33/adapter \
    runs-final/sft-qwen3-4b-tb20m-samayik33/evals-elicitation \
    > "$LOGS/elic-s33.log" 2>&1 &
run_box elic-grpo grpo runs-final/grpo-r3-final/adapter \
    runs-final/grpo-r3-finals-results/finals/final731-elicitation \
    runs-final/sft-qwen3-4b-tb20m-samayik67/adapter \
    > "$LOGS/elic-grpo.log" 2>&1 &

wait
echo "ORCHESTRATOR-DONE: $(grep -l 'ALL-DONE' $LOGS/elic-*.log 2>/dev/null | wc -l)/5 boxes finished"
