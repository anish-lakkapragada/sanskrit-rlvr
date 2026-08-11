#!/usr/bin/env python
"""Samayik chrF probe for arbitrary model+adapter combos, protocol-identical
to the GRPO eval suite (seed-42 100-pair subset, temp 0.2, 512 new tokens,
chat template with enable_thinking=False) so numbers are directly comparable
to eval/samayik_chrf points in runs/*/tensorboard.

    uv run python misc/samayik_probe.py Qwen/Qwen3-4B \
        --adapter runs/sft-qwen3-4b-opus-r1/checkpoints/checkpoint-491

Evaluates the bare base model AND (if given) base+adapter in one engine.
"""

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finetune.data import load_samayik_pairs
from finetune.evals import eval_samayik


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model")
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--num-samples", type=int, default=100)
    args = ap.parse_args()

    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    lora_kwargs = {}
    if args.adapter:
        rank = json.loads(
            (ROOT / args.adapter / "adapter_config.json").read_text()).get("r", 16)
        lora_kwargs = {"enable_lora": True, "max_lora_rank": max(rank, 16)}
    llm = LLM(model=args.model, dtype="bfloat16", max_model_len=2048,
              gpu_memory_utilization=0.85, **lora_kwargs)

    def make_generate_fn(lora_request):
        def generate_fn(prompts, n, temperature, max_new_tokens):
            texts = [tokenizer.apply_chat_template(
                [{"role": "user", "content": p}], tokenize=False,
                add_generation_prompt=True, enable_thinking=False)
                for p in prompts]
            params = SamplingParams(n=n, temperature=max(temperature, 1e-6),
                                    max_tokens=max_new_tokens)
            outs = llm.generate(texts, params, lora_request=lora_request,
                                use_tqdm=False)
            return [[o.text for o in out.outputs] for out in outs]
        return generate_fn

    pairs = load_samayik_pairs("data/eval/samayik.json")
    arms = [("base", None)]
    if args.adapter:
        from vllm.lora.request import LoRARequest

        arms.append(("adapter", LoRARequest("adapter", 1, str(ROOT / args.adapter))))
    for name, req in arms:
        metrics, _ = eval_samayik(
            make_generate_fn(req), pairs, num_samples=args.num_samples,
            temperature=0.2, max_new_tokens=512, rng=random.Random(42))
        print(f"[samayik-probe] {name} ({args.adapter if req else args.model}): "
              f"chrf={metrics['chrf']:.2f} chrf++={metrics['chrf_pp']:.2f} "
              f"tag_rate={metrics['translation_tag_rate']:.2f}")


if __name__ == "__main__":
    main()
