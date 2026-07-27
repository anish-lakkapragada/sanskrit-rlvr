#!/usr/bin/env bash
# Overnight watchdog: poll training liveness; on death, pull artifacts locally
# so checkpoints/logs survive even if the box is later terminated.
IP=147.224.143.42
LOCAL=/Users/anish/Documents/git-repos/sanskrit/runs-rescued
SSH="-o ConnectTimeout=30 -o StrictHostKeyChecking=accept-new"
for i in $(seq 1 200); do   # 200 x 10min = 33h
  st=$(ssh $SSH ubuntu@$IP 'cd ~/sanskrit
    t=$(tmux has-session -t train 2>/dev/null && echo LIVE || echo DEAD)
    p=$(tail -c 2000 train.log | tr "\r" "\n" | grep -oE "[0-9]+/1000" | tail -1)
    echo "$t $p"' 2>/dev/null)
  live=$(echo "$st" | awk '{print $1}'); prog=$(echo "$st" | awk '{print $2}')
  if [ "$live" = "DEAD" ]; then
    echo "!!! TRAINING DIED at $(date) — last progress: $prog"
    echo "--- error tail ---"
    ssh $SSH ubuntu@$IP 'cd ~/sanskrit; grep -oE "(OutOfMemoryError|ValueError|RuntimeError|ConnectionError|AssertionError|Error): .{0,200}" train.log | tail -3'
    mkdir -p "$LOCAL"
    echo "--- rescuing artifacts to $LOCAL ---"
    rsync -az --timeout=600 -e "ssh $SSH" \
      --include='*/' --include='*.json' --include='*.jsonl' --include='*.log' \
      --include='adapter_*' --include='events.out.tfevents*' --exclude='*' \
      ubuntu@$IP:~/sanskrit/runs/ "$LOCAL/" 2>&1 | tail -3
    ssh $SSH ubuntu@$IP 'cd ~/sanskrit; tail -c 3000 train.log' > "$LOCAL/train.log.tail" 2>/dev/null
    du -sh "$LOCAL" 2>/dev/null
    echo "BOX STILL RUNNING and still billing — terminate when ready:"
    echo "  instance 99efd557bcea435aa518b9cfe63f50c6"
    exit 1
  fi
  [ $((i % 6)) -eq 1 ] && echo "[$(date +%H:%M)] alive at $prog"
  sleep 600
done
echo "watchdog finished 33h without a crash"
