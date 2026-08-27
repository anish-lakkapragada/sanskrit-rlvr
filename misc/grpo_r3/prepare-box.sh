#!/bin/bash
# GRPO round-3 stage 0 on the box: merge -> tokenizer gate -> dual copies ->
# acceptance probe. STOPS after the probe; training is launched separately.
set -eu
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/sanskrit"

echo "[prepare] merging adapter into Qwen3-4B (bf16)..."
uv run --no-sync python misc/merge_adapter.py adapter-sft \
    --base Qwen/Qwen3-4B --out tb20m-samayik67-merged-train

echo "[prepare] tokenizer round-trip gate..."
uv run --no-sync python - <<'PY'
import json
from pathlib import Path
p = Path("tb20m-samayik67-merged-train/tokenizer_config.json")
cfg = json.loads(p.read_text())
if "extra_special_tokens" in cfg:
    cfg.pop("extra_special_tokens")
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    print("[fix] extra_special_tokens stripped (transformers 5.14.1 round-trip bug)")
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("tb20m-samayik67-merged-train")
assert tok("x")["input_ids"], "tokenizer failed to encode"
print("[gate] tokenizer round-trip OK")
PY

echo "[prepare] pristine read-only eval copy..."
rm -rf tb20m-samayik67-merged-eval
cp -a tb20m-samayik67-merged-train tb20m-samayik67-merged-eval
chmod -R a-w tb20m-samayik67-merged-eval

echo "[prepare] acceptance probe (seeded 64x16 on the eval copy)..."
uv run --no-sync python -m prevals.eval prevals/campaign/eval-grpo-r3-acceptance.yml

echo "[prepare] DONE"
