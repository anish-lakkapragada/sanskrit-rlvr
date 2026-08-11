#!/usr/bin/env python
"""Merge a LoRA adapter into its base model for GRPO stage-2 / vLLM serving.

Runs fine on CPU (used while the GPU is busy evaluating):
    uv run python misc/merge_adapter.py runs-eval/adapter-final \
        --base Qwen/Qwen3-4B --out sft-merged
"""

import argparse

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("adapter")
    ap.add_argument("--base", default="Qwen/Qwen3-4B")
    ap.add_argument("--out", default="sft-merged")
    args = ap.parse_args()

    model = AutoModelForCausalLM.from_pretrained(args.base, dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(model, args.adapter)
    model = model.merge_and_unload()
    model.save_pretrained(args.out)
    AutoTokenizer.from_pretrained(args.base).save_pretrained(args.out)
    print(f"[merge] {args.base} + {args.adapter} -> {args.out}")


if __name__ == "__main__":
    main()
