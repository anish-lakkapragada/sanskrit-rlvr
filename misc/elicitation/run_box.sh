#!/bin/bash
# Elicitation generation on a 1x A100 box: both prompt variants -> out-elicitation/.
# MODE=sft  : base Qwen/Qwen3-4B + adapter-main (a 20M mixture arm)
# MODE=grpo : merge adapter-sft (20M-67%) into Qwen3-4B first, then adapter-main
#             (the GRPO-r3 LoRA, whose base is that merged policy).
set -eu
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/sanskrit"
MODE="$1"
# optional overrides: single-template mode with a custom extraction tag
TEMPLATE="${2:-}"
OUTNAME="${3:-}"
EXTRACT="${4:-translation}"

if [ "$MODE" = "grpo" ]; then
    echo "[box] merging 20M-67% adapter into Qwen3-4B..."
    uv run --no-sync python misc/merge_adapter.py adapter-sft \
        --base Qwen/Qwen3-4B --out merged-base
    uv run --no-sync python - <<'PY'
import json
from pathlib import Path
p = Path("merged-base/tokenizer_config.json")
cfg = json.loads(p.read_text())
if cfg.pop("extra_special_tokens", None) is not None:
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    print("[fix] extra_special_tokens stripped")
from transformers import AutoTokenizer
assert AutoTokenizer.from_pretrained("merged-base")("x")["input_ids"]
print("[gate] tokenizer round-trip OK")
PY
    MODEL=merged-base
else
    MODEL=Qwen/Qwen3-4B
fi

if [ -n "$TEMPLATE" ]; then
    uv run --no-sync python misc/final_translation_eval.py \
        --model "$MODEL" --adapter adapter-main --only samayik \
        --templates "$TEMPLATE" --out-names "$OUTNAME" \
        --extract-tag "$EXTRACT" --out-dir out-elicitation
else
    uv run --no-sync python misc/final_translation_eval.py \
        --model "$MODEL" --adapter adapter-main --only samayik \
        --templates prompts/v1/translation-elicitation/translation_scaffold.txt \
                    prompts/v1/translation-elicitation/translation_placebo.txt \
        --out-names samayik-scaffold.json samayik-placebo.json \
        --out-dir out-elicitation
fi
echo "BOX-DONE"
