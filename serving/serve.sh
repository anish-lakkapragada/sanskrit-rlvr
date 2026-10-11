#!/bin/bash
# One-command serving app: ./serving/serve.sh          -> launch/reuse box, serve, open UI
#                          ./serving/serve.sh stop     -> terminate the box
# Box: 1x A100 SXM4 (us-east-1, ~$2/h), name serve-20m, 6h self-terminate backstop.
set -u
cd "$(dirname "$0")/.."
source .env
KEY="${LAMBDA_API_KEY:-$LAMBDA_CLOUD_API_KEY}"
SSH="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15"
NAME=serve-20m

api() { curl -su "$KEY:" "$@"; }

instance_json() {
    api https://cloud.lambdalabs.com/api/v1/instances | python3 -c "
import json, sys
for i in json.load(sys.stdin)['data']:
    if i['name'] == '$NAME':
        print(i['id'], i['status'], i.get('ip') or '-')
        break"
}

if [ "${1:-}" = "stop" ]; then
    read -r ID STATUS IP <<<"$(instance_json)" || true
    if [ -z "${ID:-}" ]; then echo "no $NAME instance found"; exit 0; fi
    api -X POST https://cloud.lambdalabs.com/api/v1/instance-operations/terminate \
        -H "Content-Type: application/json" -d "{\"instance_ids\":[\"$ID\"]}" >/dev/null
    echo "terminate requested for $NAME ($ID); verifying..."
    for _ in $(seq 1 20); do
        left=$(api https://cloud.lambdalabs.com/api/v1/instances | python3 -c \
            "import json,sys; print(len(json.load(sys.stdin)['data']))")
        [ "$left" = "0" ] && { echo "NONE remaining."; exit 0; }
        sleep 10
    done
    echo "still terminating — re-check with: ./serving/serve.sh status"; exit 0
fi

if [ "${1:-}" = "status" ]; then
    instance_json; exit 0
fi

# ---- persistent filesystem (fast respins after termination) ----------------
FS_NAME=sanskrit-serve
fs_exists() {
    api https://cloud.lambdalabs.com/api/v1/file-systems | python3 -c "
import json, sys
for f in json.load(sys.stdin).get('data', []):
    if f.get('name') == '$FS_NAME' and f.get('region', {}).get('name') == 'us-east-1':
        print('yes'); break"
}
FS_ARG=""
if [ "$(fs_exists)" = "yes" ]; then
    FS_ARG=",\"file_system_names\":[\"$FS_NAME\"]"
    echo "[serve] persistent filesystem '$FS_NAME' will be attached"
else
    echo "[serve] creating persistent filesystem '$FS_NAME' (us-east-1)..."
    api -X POST https://cloud.lambdalabs.com/api/v1/filesystems \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"$FS_NAME\",\"region\":\"us-east-1\"}" >/dev/null 2>&1 || true
    if [ "$(fs_exists)" = "yes" ]; then
        FS_ARG=",\"file_system_names\":[\"$FS_NAME\"]"
        echo "[serve] filesystem created and will be attached"
    else
        echo "[serve] WARNING: could not create '$FS_NAME' via API — create it once in"
        echo "        the Lambda dashboard (Storage > us-east-1) for ~10min respins."
    fi
fi

# ---- launch or reuse -------------------------------------------------------
read -r ID STATUS IP <<<"$(instance_json)" || true
if [ -z "${ID:-}" ]; then
    echo "[serve] launching $NAME (1x A100 SXM4, us-east-1)..."
    api -X POST https://cloud.lambdalabs.com/api/v1/instance-operations/launch \
        -H "Content-Type: application/json" \
        -d "{\"region_name\":\"us-east-1\",\"instance_type_name\":\"gpu_1x_a100_sxm4\",\"ssh_key_names\":[\"anish-mac\"],\"name\":\"$NAME\",\"quantity\":1$FS_ARG}" \
        | python3 -c "import json,sys; d=json.load(sys.stdin); print('[serve] launched:', d.get('data',{}).get('instance_ids', d.get('error')))"
fi

echo "[serve] waiting for active instance + IP..."
for _ in $(seq 1 80); do
    read -r ID STATUS IP <<<"$(instance_json)" || true
    [ "${STATUS:-}" = "active" ] && [ "${IP:-}" != "-" ] && break
    sleep 15
done
[ "${STATUS:-}" != "active" ] && { echo "[serve] box never became active"; exit 1; }
echo "[serve] $NAME active at $IP"

# fresh box needs a settle window past the fake-ready sshd
$SSH ubuntu@"$IP" "test -f ~/sanskrit/.setup-done" 2>/dev/null || sleep 45

# ---- payload ---------------------------------------------------------------
echo "[serve] syncing payload..."
retry() { for w in 20 40 60 90 120 120; do "$@" && return 0; echo "  retry in ${w}s"; sleep "$w"; done; return 1; }
retry rsync -az -e "$SSH" pyproject.toml uv.lock README.md ubuntu@"$IP":~/sanskrit/
retry rsync -az -e "$SSH" -r finetune misc prompts serving ubuntu@"$IP":~/sanskrit/

# restore adapters from the persistent filesystem if present, then upload only
# the ones still missing (first run uploads all; later runs upload none)
$SSH ubuntu@"$IP" "for d in /lambda/nfs/$FS_NAME ~/$FS_NAME; do [ -d \$d/artifacts ] && mkdir -p ~/sanskrit && cp -an \$d/artifacts/adapter-* ~/sanskrit/ 2>/dev/null; done; true"
for pair in "adapter-s100 runs-final/sft-qwen3-4b-tb20m-samayik100/adapter" \
            "adapter-s67 runs-final/sft-qwen3-4b-tb20m-samayik67/adapter" \
            "adapter-s50 runs-final/sft-qwen3-4b-tb20m-samayik50/adapter" \
            "adapter-s33 runs-final/sft-qwen3-4b-tb20m-samayik33/adapter" \
            "adapter-t20s0 runs-final/sft-qwen3-4b-tb20m-samayik0/adapter" \
            "adapter-t10s100 runs-final/sft-qwen3-4b-tb10m-samayik100/adapter" \
            "adapter-t10s67 runs-final/sft-qwen3-4b-tb10m-samayik67/adapter" \
            "adapter-t10s50 runs-final/sft-qwen3-4b-tb10m-samayik50/adapter" \
            "adapter-t10s33 runs-final/sft-qwen3-4b-tb10m-samayik33/adapter" \
            "adapter-t10s0 runs-final/sft-qwen3-4b-tb10m-samayik0/adapter" \
            "adapter-t15s100 runs-final/sft-qwen3-4b-tb15m-samayik100/adapter" \
            "adapter-t15s67 runs-final/sft-qwen3-4b-tb15m-samayik67/adapter" \
            "adapter-t15s50 runs-final/sft-qwen3-4b-tb15m-samayik50/adapter" \
            "adapter-t15s33 runs-final/sft-qwen3-4b-tb15m-samayik33/adapter" \
            "adapter-t15s0 runs-final/sft-qwen3-4b-tb15m-samayik0/adapter" \
            "adapter-grpo runs-final/grpo-r3-final/adapter"; do
    set -- $pair
    if ! $SSH ubuntu@"$IP" "test -f ~/sanskrit/$1/adapter_model.safetensors" 2>/dev/null; then
        retry rsync -az -e "$SSH" -r "$2/" ubuntu@"$IP":~/sanskrit/"$1"/
    fi
done

# Keep cleanup separate so pkill cannot match the shell launching the new timer.
$SSH ubuntu@"$IP" "pkill -f '[s]leep 21600' 2>/dev/null || true"
$SSH ubuntu@"$IP" "nohup bash -c 'sleep 21600; curl -su ${KEY}: -X POST https://cloud.lambdalabs.com/api/v1/instance-operations/terminate -H \"Content-Type: application/json\" -d \"{\\\"instance_ids\\\":[\\\"$ID\\\"]}\"' >/dev/null 2>&1 &"
echo "[serve] 6h self-terminate backstop armed"

# ---- provision + start servers --------------------------------------------
echo "[serve] provisioning box (first run: ~20-30 min incl. model download)..."
$SSH ubuntu@"$IP" "cd ~/sanskrit && bash serving/box_setup.sh" || { echo "[serve] box setup FAILED"; exit 1; }

# ---- tunnels + local app ----------------------------------------------------
echo "[serve] opening tunnels (8000, 8001)..."
pkill -f "ssh.*-L 8000:localhost:8000.*$IP" 2>/dev/null || true
$SSH -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -f -N -L 8000:localhost:8000 -L 8001:localhost:8001 ubuntu@"$IP"
trap 'pkill -f "ssh.*-L 8000:localhost:8000" 2>/dev/null; echo; echo "[serve] tunnels closed. Box is STILL RUNNING (~\$2/h) — stop with: ./serving/serve.sh stop"' EXIT

echo "[serve] READY — starting local UI at http://localhost:7860 (Ctrl-C to quit)"
uv run --no-project --with fastapi --with "uvicorn[standard]" --with httpx python serving/app.py
