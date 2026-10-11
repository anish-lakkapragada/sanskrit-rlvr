#!/bin/bash
# Box-side provisioning for the serving app: env (driver-570 cu128 stack via
# misc/grpo_r3/setup-box.sh), GRPO base merge + tokenizer gate, then two vLLM
# OpenAI servers under nohup:
#   :8000  Qwen/Qwen3-4B + the four 20M mixture arms as LoRA modules
#   :8001  merged 20M-67% base + the GRPO-r3 adapter as a LoRA module
set -eu
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/sanskrit"

# Persistent filesystem: park caches + built artifacts so respins skip the
# slow work (env wheels, HF download, GRPO merge, adapter uploads).
FS=""
for cand in /lambda/nfs/sanskrit-serve "$HOME/sanskrit-serve"; do
    [ -d "$cand" ] && FS="$cand" && break
done
if [ -n "$FS" ] && [ -d "$FS" ]; then
    mkdir -p "$FS/uv-cache" "$FS/hf-cache" "$FS/artifacts"
    mkdir -p "$HOME/.cache"
    [ -L "$HOME/.cache/uv" ] || { rm -rf "$HOME/.cache/uv"; ln -s "$FS/uv-cache" "$HOME/.cache/uv"; }
    [ -L "$HOME/.cache/huggingface" ] || { rm -rf "$HOME/.cache/huggingface"; ln -s "$FS/hf-cache" "$HOME/.cache/huggingface"; }
    [ -d "$FS/artifacts/merged-s67" ] && [ ! -d merged-s67 ] && cp -r "$FS/artifacts/merged-s67" merged-s67
    echo "[serve-box] persistent filesystem active at $FS"
fi

if [ ! -f .setup-done ]; then
    bash misc/grpo_r3/setup-box.sh
    touch .setup-done
fi

if [ ! -d merged-s67 ]; then
    echo "[serve-box] merging 20M-67% adapter into Qwen3-4B (GRPO base)..."
    uv run --no-sync python misc/merge_adapter.py adapter-s67 \
        --base Qwen/Qwen3-4B --out merged-s67
    uv run --no-sync python - <<'PY'
import json
from pathlib import Path
p = Path("merged-s67/tokenizer_config.json")
cfg = json.loads(p.read_text())
if cfg.pop("extra_special_tokens", None) is not None:
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    print("[fix] extra_special_tokens stripped")
from transformers import AutoTokenizer
assert AutoTokenizer.from_pretrained("merged-s67")("x")["input_ids"]
print("[gate] tokenizer round-trip OK")
PY
fi

# save built artifacts to the filesystem for the next cold start
if [ -n "$FS" ] && [ -d "$FS" ]; then
    [ -d "$FS/artifacts/merged-s67" ] || cp -r merged-s67 "$FS/artifacts/merged-s67"
    for a in adapter-s100 adapter-s67 adapter-s50 adapter-s33 adapter-grpo \
             adapter-t10s100 adapter-t10s67 adapter-t10s50 adapter-t10s33 adapter-t10s0 \
             adapter-t15s100 adapter-t15s67 adapter-t15s50 adapter-t15s33 adapter-t15s0 \
             adapter-t20s0; do
        [ -d "$FS/artifacts/$a" ] || { [ -d "$a" ] && cp -r "$a" "$FS/artifacts/$a"; }
    done
    echo "[serve-box] artifacts cached to filesystem"
fi

# ½-alpha "-avg" twins of every adapter: same weights (hardlinked), alpha
# halved in the config, so vLLM applies 0.5·ΔW — the exact 50/50 average of
# the fine-tuned model with its serving base. Registered post-start below.
echo "[serve-box] building -avg adapter variants..."
python3 - <<'PY'
import json, os, shutil
from pathlib import Path
for src in sorted(Path(".").glob("adapter-*")):
    if not src.is_dir() or src.name.endswith("-avg"):
        continue
    cfgp = src / "adapter_config.json"
    if not cfgp.exists():
        continue
    dst = Path(src.name + "-avg")
    if not dst.exists():
        shutil.copytree(src, dst, copy_function=os.link)
    cfg = json.loads(cfgp.read_text())
    cfg["lora_alpha"] = cfg["lora_alpha"] / 2
    (dst / "adapter_config.json").unlink()  # break hardlink before rewrite
    (dst / "adapter_config.json").write_text(json.dumps(cfg, indent=2))
    print(f"  {dst.name}: lora_alpha {cfg['lora_alpha']*2} -> {cfg['lora_alpha']}")
PY

export VLLM_ATTENTION_BACKEND=FLASH_ATTN
export VLLM_USE_FLASHINFER_SAMPLER=0
# allow zero-downtime adapter registration on the running servers:
#   curl localhost:8000/v1/load_lora_adapter -d '{"lora_name":"x","lora_path":"/home/ubuntu/sanskrit/adapter-x"}'
export VLLM_ALLOW_RUNTIME_LORA_UPDATING=true

pkill -f "vllm serve" 2>/dev/null || true
sleep 3
pkill -9 -f "Engine[C]ore" 2>/dev/null || true
sleep 2

free_vram=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
echo "[serve-box] VRAM in use before start: ${free_vram} MiB (must be ~0)"

wait_port() {  # $1 port  $2 logfile  $3 tries
    for i in $(seq 1 "$3"); do
        ok=$(curl -s -o /dev/null -w "%{http_code}" "localhost:$1/v1/models" || true)
        [ "$ok" = "200" ] && return 0
        if grep -q "Engine core initialization failed\|CUDA out of memory" "$2" 2>/dev/null; then
            echo "[serve-box] $2 shows fatal init error:"; tail -8 "$2"; return 1
        fi
        sleep 10
    done
    echo "[serve-box] TIMEOUT on port $1"; tail -20 "$2"; return 1
}

echo "[serve-box] starting server A (:8000, base + 4 SFT LoRAs)..."
nohup uv run --no-sync vllm serve Qwen/Qwen3-4B \
    --port 8000 --dtype bfloat16 --max-model-len 8192 \
    --gpu-memory-utilization 0.44 --enforce-eager \
    --enable-lora --max-lora-rank 64 --max-loras 6 \
    --lora-modules \
        tb10m-samayik100=adapter-t10s100 tb10m-samayik67=adapter-t10s67 \
        tb10m-samayik50=adapter-t10s50 tb10m-samayik33=adapter-t10s33 \
        tb10m-samayik0=adapter-t10s0 \
        tb15m-samayik100=adapter-t15s100 tb15m-samayik67=adapter-t15s67 \
        tb15m-samayik50=adapter-t15s50 tb15m-samayik33=adapter-t15s33 \
        tb15m-samayik0=adapter-t15s0 \
        tb20m-samayik100=adapter-s100 tb20m-samayik67=adapter-s67 \
        tb20m-samayik50=adapter-s50 tb20m-samayik33=adapter-s33 \
        tb20m-samayik0=adapter-t20s0 \
        tb10m-samayik100-avg=adapter-t10s100-avg tb10m-samayik67-avg=adapter-t10s67-avg \
        tb10m-samayik50-avg=adapter-t10s50-avg tb10m-samayik33-avg=adapter-t10s33-avg \
        tb10m-samayik0-avg=adapter-t10s0-avg \
        tb15m-samayik100-avg=adapter-t15s100-avg tb15m-samayik67-avg=adapter-t15s67-avg \
        tb15m-samayik50-avg=adapter-t15s50-avg tb15m-samayik33-avg=adapter-t15s33-avg \
        tb15m-samayik0-avg=adapter-t15s0-avg \
        tb20m-samayik100-avg=adapter-s100-avg tb20m-samayik67-avg=adapter-s67-avg \
        tb20m-samayik50-avg=adapter-s50-avg tb20m-samayik33-avg=adapter-s33-avg \
        tb20m-samayik0-avg=adapter-t20s0-avg \
    > serveA.log 2>&1 &
wait_port 8000 serveA.log 90 || exit 1
echo "[serve-box] server A ready (incl. -avg LoRAs); starting server B (:8001, merged-67 + GRPO LoRA)..."

nohup uv run --no-sync vllm serve merged-s67 \
    --served-model-name merged-s67 \
    --port 8001 --dtype bfloat16 --max-model-len 8192 \
    --gpu-memory-utilization 0.40 --enforce-eager \
    --enable-lora --max-lora-rank 64 \
    --lora-modules grpo-r3=adapter-grpo grpo-r3-avg=adapter-grpo-avg \
    > serveB.log 2>&1 &
wait_port 8001 serveB.log 90 || exit 1
echo "[serve-box] SERVERS-READY (grpo-r3-avg anchors to merged-s67, not stock Qwen3)"
