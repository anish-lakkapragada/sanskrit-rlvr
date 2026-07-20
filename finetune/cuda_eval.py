"""CUDA-side checkpoint evaluation: batched bf16 generation via transformers.

common.eval_checkpoint delegates here when a run's backend is "cuda".
Checkpoints come in two flavors — a full model dir (SFT saves these) or a
PEFT adapter dir (GRPO) — and both collapse into one merged model for
generation. Judging and metrics are shared with the mlx path (common.py).
"""

import gc
from pathlib import Path

from .common import judge_rows, summarize


def _load(base: str, ckpt: Path | None):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    full = bool(ckpt) and (Path(ckpt) / "config.json").exists()
    src = str(ckpt) if full else base
    tok = AutoTokenizer.from_pretrained(src)
    model = AutoModelForCausalLM.from_pretrained(
        src, dtype="bfloat16", device_map="cuda")
    if ckpt and not full:  # PEFT adapter dir
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, str(ckpt)).merge_and_unload()
    return model.eval(), tok


def _generate_all(model, tok, rows, temp, max_tokens=384, batch_size=16):
    import torch
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    prompts = [tok.apply_chat_template(
        [{"role": "system", "content": r["system"]},
         {"role": "user", "content": r["prompt"]}],
        add_generation_prompt=True, tokenize=False) for r in rows]
    out = []
    for i in range(0, len(prompts), batch_size):
        enc = tok(prompts[i:i + batch_size], return_tensors="pt",
                  padding=True).to(model.device)
        with torch.no_grad():
            gen = model.generate(
                **enc, max_new_tokens=max_tokens,
                do_sample=temp > 0,
                temperature=temp if temp > 0 else None,
                pad_token_id=tok.pad_token_id)
        out += tok.batch_decode(gen[:, enc["input_ids"].shape[1]:],
                                skip_special_tokens=True)
    return out


def eval_checkpoint_cuda(base: str, ckpt: Path | None, rows: list[dict],
                         temp: float = 0.0) -> tuple[dict, list[dict]]:
    import torch
    model, tok = _load(base, ckpt)
    records = judge_rows(rows, _generate_all(model, tok, rows, temp))
    del model
    gc.collect()
    torch.cuda.empty_cache()
    return summarize(records), records
