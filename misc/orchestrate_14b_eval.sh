#!/bin/bash
# Qwen3-14B base VP-eval scale probe: two 1x A100 boxes (thinking off / on),
# each self-terminating; results pulled to runs-final/data-mixture/.
# Usage: bash misc/orchestrate_14b_eval.sh   (run in background; logs to
# runs-final/elicitation-logs/q14b-*.log)
set -u
cd "$(dirname "$0")/.."
source .env
KEY="${LAMBDA_API_KEY:-$LAMBDA_CLOUD_API_KEY}"
SSH="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15"
LOGS=runs-final/elicitation-logs
mkdir -p "$LOGS"

ip_of() {
    curl -su "$KEY:" https://cloud.lambdalabs.com/api/v1/instances | python3 -c "
import json, sys
for i in json.load(sys.stdin)['data']:
    if i['name'] == '$1' and i['status'] == 'active' and i.get('ip'):
        print(i['id'], i['ip'])"
}

retry_rsync() {
    for w in 20 40 60 90 120 120; do
        rsync -az -e "$SSH" "$@" && return 0
        echo "  rsync retry in ${w}s"; sleep "$w"
    done
    return 1
}

run_eval_box() {  # $1=box_name  $2=config  $3=suite_name
    local name="$1" cfg="$2" suite="$3" id="" ip=""
    curl -su "$KEY:" -X POST https://cloud.lambdalabs.com/api/v1/instance-operations/launch \
        -H "Content-Type: application/json" \
        -d "{\"region_name\":\"us-east-1\",\"instance_type_name\":\"gpu_1x_a100_sxm4\",\"ssh_key_names\":[\"anish-mac\"],\"name\":\"$name\",\"quantity\":1}" >/dev/null
    for _ in $(seq 1 80); do
        read -r id ip <<<"$(ip_of "$name")" || true
        [ -n "${ip:-}" ] && break
        sleep 15
    done
    [ -z "${ip:-}" ] && { echo "[$name] never active"; return 1; }
    echo "[$name] active at $ip"; sleep 45

    retry_rsync pyproject.toml uv.lock README.md "ubuntu@$ip:~/sanskrit/" || return 1
    retry_rsync -r finetune misc prompts prevals "ubuntu@$ip:~/sanskrit/" || return 1
    retry_rsync -R data/data-mixture/eval/vp-eval.json "ubuntu@$ip:~/sanskrit/" || return 1
    echo "[$name] payload synced"

    # 10h self-terminate backstop
    $SSH "ubuntu@$ip" "nohup bash -c 'sleep 36000; curl -su ${KEY}: -X POST \
        https://cloud.lambdalabs.com/api/v1/instance-operations/terminate \
        -H \"Content-Type: application/json\" \
        -d \"{\\\"instance_ids\\\":[\\\"$id\\\"]}\"' >/dev/null 2>&1 &"

    $SSH "ubuntu@$ip" "cd ~/sanskrit && bash misc/grpo_r3/setup-box.sh" || return 1
    $SSH "ubuntu@$ip" "export PATH=\$HOME/.local/bin:\$PATH && cd ~/sanskrit && uv run --no-sync python -c \
        'from huggingface_hub import snapshot_download; snapshot_download(\"Qwen/Qwen3-14B\")'" || return 1
    echo "[$name] env + model ready; starting eval ($suite)"
    $SSH "ubuntu@$ip" "export PATH=\$HOME/.local/bin:\$PATH && cd ~/sanskrit && nohup uv run --no-sync python -m prevals.eval $cfg > eval.log 2>&1 & echo started"

    # poll: done when the suite output dir has summary.json; fail on FAILED/Traceback
    for _ in $(seq 1 400); do
        state=$($SSH "ubuntu@$ip" "
            if ls ~/sanskrit/prevals/outputs/data-mixture/$suite/*/summary.json >/dev/null 2>&1; then echo DONE;
            elif grep -laq 'FAILED\|Traceback' ~/sanskrit/eval.log 2>/dev/null && ! pgrep -f 'prevals.eval' >/dev/null; then echo FAILED;
            else tail -c 300 ~/sanskrit/eval.log 2>/dev/null | tr '\n' ' ' | tail -c 120; fi" 2>/dev/null)
        case "$state" in
            DONE) break ;;
            FAILED) echo "[$name] EVAL FAILED:"; $SSH "ubuntu@$ip" "tail -20 ~/sanskrit/eval.log" 2>/dev/null; return 1 ;;
            *) echo "[$name] $(date '+%H:%M') $state" ;;
        esac
        sleep 60
    done

    mkdir -p "runs-final/data-mixture/$suite"
    retry_rsync -r "ubuntu@$ip:~/sanskrit/prevals/outputs/data-mixture/$suite/" \
        "runs-final/data-mixture/$suite/" || return 1
    echo "[$name] results pulled -> runs-final/data-mixture/$suite/"

    curl -su "$KEY:" -X POST https://cloud.lambdalabs.com/api/v1/instance-operations/terminate \
        -H "Content-Type: application/json" -d "{\"instance_ids\":[\"$id\"]}" >/dev/null
    echo "[$name] terminate requested"
    echo "[$name] ALL-DONE"
}

run_eval_box q14b-nothink prevals/campaign/eval-base-qwen3-14b-nothink.yml dm-base-qwen3-14b-nothink \
    > "$LOGS/q14b-nothink.log" 2>&1 &
run_eval_box q14b-think prevals/campaign/eval-base-qwen3-14b-think.yml dm-base-qwen3-14b-think \
    > "$LOGS/q14b-think.log" 2>&1 &
wait
echo "Q14B-ORCHESTRATOR-DONE: $(grep -l 'ALL-DONE' $LOGS/q14b-*.log 2>/dev/null | wc -l)/2"
