#!/usr/bin/env python
"""Final-state EN->SA translation eval on Samayik + FLORES-200.

Scores the two 750-pair contamination-free validation sets (built by
misc/data/make_standard_sft_data.py; no normalized EN/SA sentence is shared
with either *_finetune.json corpus). Generation protocol matches the GRPO
eval suite / misc/samayik_probe.py: temperature 0.2, chat template with
enable_thinking=False, chrF/chrF++ on <translation>-extracted text,
max_new_tokens 4096. --num-samples 0 (default) means the full set.

NOT comparable to pre-rework final-*.json artifacts, which drew 500 seed-42
pairs from the full data/eval/ corpora (contaminated for samayik-trained arms).

    python misc/final_translation_eval.py --model Qwen/Qwen3-4B \
        [--adapter PATH] --out-dir OUT

Writes OUT/final-samayik.json and OUT/final-flores-200.json, each
{"meta": ..., "metrics": ..., "samples": [{"en","ref","hyp","raw"}, ...]}.
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path

# A100 boxes whose flashinfer cubins don't match the installed vLLM build fall
# back to a ninja JIT that isn't available; the built-in backends are fine.
os.environ.setdefault("VLLM_ATTENTION_BACKEND", "FLASH_ATTN")
os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finetune.data import load_samayik_pairs
from finetune.evals import eval_samayik

DATASETS = (
    # the data-mixture campaign's canonical eval files: samayik-eval.json is the
    # 750-pair contamination-group holdout; flores-200.json is the FULL 2,009-pair
    # corpus (no FLORES data appears in any mixture, so the full set is clean).
    ("samayik", "data/data-mixture/eval/samayik-eval.json"),
    ("flores-200", "data/data-mixture/eval/flores-200.json"),
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--num-samples", type=int, default=0,
                    help="0 = every pair in the validation set")
    ap.add_argument("--max-new-tokens", type=int, default=4096)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--only", default=None, choices=[n for n, _ in DATASETS],
                    help="run a single dataset instead of both")
    ap.add_argument("--templates", nargs="+", default=None,
                    help="prompt-template files ({english} slot); one output "
                         "file per template, all served from one engine")
    ap.add_argument("--out-names", nargs="+", default=None,
                    help="output filenames zipped with --templates")
    ap.add_argument("--extract-tag", default="translation",
                    choices=["translation", "answer"],
                    help="tag the hypothesis is extracted from")
    args = ap.parse_args()
    if args.templates and (not args.out_names
                           or len(args.out_names) != len(args.templates)):
        ap.error("--templates requires an equal-length --out-names")

    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    lora_kwargs, lora_request = {}, None
    if args.adapter:
        rank = json.loads(
            (Path(args.adapter) / "adapter_config.json").read_text()).get("r", 16)
        lora_kwargs = {"enable_lora": True, "max_lora_rank": max(rank, 16)}
    llm = LLM(model=args.model, dtype="bfloat16", max_model_len=8192,
              gpu_memory_utilization=0.90, enforce_eager=True, **lora_kwargs)
    if args.adapter:
        from vllm.lora.request import LoRARequest

        lora_request = LoRARequest("adapter", 1, args.adapter)

    def generate_fn(prompts, n, temperature, max_new_tokens):
        texts = [tokenizer.apply_chat_template(
            [{"role": "user", "content": p}], tokenize=False,
            add_generation_prompt=True, enable_thinking=False)
            for p in prompts]
        params = SamplingParams(n=n, temperature=max(temperature, 1e-6),
                                max_tokens=max_new_tokens)
        outs = llm.generate(texts, params, lora_request=lora_request,
                            use_tqdm=True)
        return [[o.text for o in out.outputs] for out in outs]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    datasets = [(n, p) for n, p in DATASETS if args.only in (None, n)]
    # (template_path_or_None, template_string_or_None, output_filename)
    if args.templates:
        jobs = [(t, Path(t).read_text(), o)
                for t, o in zip(args.templates, args.out_names)]
    else:
        jobs = [("v0/translation.txt", None, None)]
    for name, rel_path in datasets:
        pairs = load_samayik_pairs(ROOT / rel_path)
        num_samples = args.num_samples or len(pairs)
        for tpl_path, tpl_text, out_name in jobs:
            metrics, samples = eval_samayik(
                generate_fn, pairs, num_samples=num_samples,
                temperature=args.temperature,
                max_new_tokens=args.max_new_tokens,
                rng=random.Random(42), template=tpl_text,
                extract_tag=args.extract_tag)
            payload = {
                "meta": {"model": args.model, "adapter": args.adapter,
                         "dataset": rel_path, "num_samples": num_samples,
                         "temperature": args.temperature,
                         "max_new_tokens": args.max_new_tokens, "seed": 42,
                         "prompt_template": tpl_path},
                "metrics": metrics,
                "samples": samples,
            }
            fname = out_name or f"final-{name}.json"
            (out_dir / fname).write_text(
                json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
            print(f"[final-eval] {name} [{tpl_path}]: "
                  f"chrf={metrics['chrf']:.2f} "
                  f"chrf++={metrics['chrf_pp']:.2f} "
                  f"tag_rate={metrics['translation_tag_rate']:.2f}", flush=True)


if __name__ == "__main__":
    main()
