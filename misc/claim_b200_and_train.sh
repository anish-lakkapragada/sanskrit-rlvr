#!/usr/bin/env bash
# Poll Lambda for 1x B200 capacity, claim the first one, set it up and start
# the gemma4-26b vp_exact run plus TensorBoard. Run from the repo root:
#   bash misc/claim_b200_and_train.sh
#
# State is written to /tmp/b200_claim.env (IP, instance id) so a tunnel can be
# opened afterwards. SSH uses a multiplexed control socket on purpose: one
# connection per minute against a loaded box exhausts sshd's MaxStartups and
# locks you out of your own machine.
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG=${CONFIG:-configs/vp-exact-gemma4-26b-1xb200.yml}
RUN_NAME=${RUN_NAME:-vp-exact-gemma4-26b}
INSTANCE_TYPE=${INSTANCE_TYPE:-gpu_1x_b200_sxm6}
MAX_POLLS=${MAX_POLLS:-720}         # 720 x 60s = 12h
STATE=/tmp/b200_claim.env

source "$REPO_DIR/.env"
SSH_OPTS=(-o ControlMaster=auto -o ControlPath=/tmp/ssh-claim-%r@%h:%p
          -o ControlPersist=15m -o StrictHostKeyChecking=accept-new
          -o ConnectTimeout=30 -o ServerAliveInterval=30)
api() { curl -s -u "$LAMBDA_API_KEY:" "$@"; }

# ---- 1. poll for capacity, then claim -------------------------------------
INSTANCE_ID=""
for i in $(seq 1 "$MAX_POLLS"); do
  region=$(api https://cloud.lambdalabs.com/api/v1/instance-types | python3 -c "
import json,sys
d=json.load(sys.stdin)['data'].get('$INSTANCE_TYPE')
r=d['regions_with_capacity_available'] if d else []
print(r[0]['name'] if r else '')
" 2>/dev/null)

  if [ -n "$region" ]; then
    echo "[$i] capacity in $region -- claiming"
    resp=$(api https://cloud.lambdalabs.com/api/v1/instance-operations/launch \
      -H "Content-Type: application/json" \
      -d "{\"region_name\":\"$region\",\"instance_type_name\":\"$INSTANCE_TYPE\",\"ssh_key_names\":[\"anish-mac\"],\"name\":\"$RUN_NAME\"}")
    INSTANCE_ID=$(echo "$resp" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(d.get('data',{}).get('instance_ids',[''])[0])
" 2>/dev/null)
    if [ -n "$INSTANCE_ID" ]; then
      echo "CLAIMED $INSTANCE_ID in $region"
      break
    fi
    echo "[$i] claim lost: $(echo "$resp" | head -c 200)"   # someone else took it
  else
    [ $((i % 10)) -eq 1 ] && echo "[$i] no B200 capacity yet"
  fi
  sleep 60
done

[ -z "$INSTANCE_ID" ] && { echo "GAVE UP: no B200 within $MAX_POLLS polls"; exit 1; }

# ---- 2. wait for boot ------------------------------------------------------
IP=""
for i in $(seq 1 40); do
  read -r st ip <<<"$(api "https://cloud.lambdalabs.com/api/v1/instances/$INSTANCE_ID" | python3 -c "
import json,sys
d=json.load(sys.stdin)['data']; print(d['status'], d.get('ip') or '')
" 2>/dev/null)"
  echo "[boot $i] $st $ip"
  if [ "$st" = "active" ] && [ -n "$ip" ]; then IP=$ip; break; fi
  if [ "$st" = "terminated" ]; then echo "FAILED: instance terminated during boot"; exit 1; fi
  sleep 30
done
[ -z "$IP" ] && { echo "FAILED: never became active"; exit 1; }

printf 'B200_IP=%s\nB200_ID=%s\n' "$IP" "$INSTANCE_ID" > "$STATE"
echo "ACTIVE $IP (state written to $STATE)"

# ---- 3. wait for sshd, then set up ----------------------------------------
for i in $(seq 1 30); do
  ssh "${SSH_OPTS[@]}" "ubuntu@$IP" true 2>/dev/null && { echo "ssh up"; break; }
  echo "[ssh $i] waiting for sshd"
  sleep 20
done

echo "=== running setup (clone, uv sync, dry-run) ==="
if ! ssh "${SSH_OPTS[@]}" "ubuntu@$IP" 'bash -s' < "$REPO_DIR/misc/setup_box.sh" "$CONFIG" 2>&1 | tail -25; then
  echo "SETUP FAILED on $IP"; exit 1
fi

# ---- 4. start training + tensorboard --------------------------------------
echo "=== starting training and tensorboard ==="
ssh "${SSH_OPTS[@]}" "ubuntu@$IP" bash -s <<EOF
set -e
cd ~/sanskrit
source ~/sanskrit/.gpu_env
tmux kill-session -t train 2>/dev/null || true
tmux kill-session -t tb 2>/dev/null || true
tmux new-session -d -s train "cd ~/sanskrit && source ~/sanskrit/.gpu_env && uv run python -m finetune.grpo --config $CONFIG --force 2>&1 | tee train.log"
mkdir -p runs/$RUN_NAME/tensorboard
tmux new-session -d -s tb "cd ~/sanskrit && source ~/sanskrit/.gpu_env && uv run tensorboard --logdir runs --host 127.0.0.1 --port 6006"
sleep 5
tmux has-session -t train && echo "train session: LIVE"
tmux has-session -t tb && echo "tensorboard session: LIVE"
EOF

echo
echo "==================== B200 CLAIMED AND TRAINING ===================="
echo "  ip:          $IP"
echo "  instance:    $INSTANCE_ID"
echo "  config:      $CONFIG"
echo "  logs:        ssh ubuntu@$IP 'tail -f ~/sanskrit/train.log'"
echo "  tensorboard: ssh -N -L 6006:127.0.0.1:6006 ubuntu@$IP   # then http://localhost:6006"
echo "==================================================================="
