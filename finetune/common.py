"""Shared pieces: generation, checkpoint evaluation, metrics writing."""

import json
import shutil
import tempfile
from pathlib import Path

from .lean import check
from .reward import extract, normalize, reward

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"


def load_model(base: str, adapter: str | None = None):
    from mlx_lm import load
    return load(base, adapter_path=adapter)


def generate(model, tok, system: str, prompt: str, max_tokens=384, temp=0.0):
    from mlx_lm import generate as _gen
    kwargs = {}
    if temp > 0:
        from mlx_lm.sample_utils import make_sampler
        kwargs["sampler"] = make_sampler(temp=temp)
    p = tok.apply_chat_template(
        [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        add_generation_prompt=True, tokenize=False)
    return _gen(model, tok, prompt=p, max_tokens=max_tokens, verbose=False, **kwargs)


def adapter_dir_for(checkpoint_file: Path) -> str:
    """mlx_lm.load wants a dir with adapters.safetensors + adapter_config.json;
    intermediate checkpoints are bare .safetensors files."""
    if checkpoint_file.name == "adapters.safetensors":
        return str(checkpoint_file.parent)
    tmp = Path(tempfile.mkdtemp(prefix="ckpt_"))
    shutil.copy(checkpoint_file, tmp / "adapters.safetensors")
    shutil.copy(checkpoint_file.parent / "adapter_config.json", tmp)
    return str(tmp)


def judge_rows(model, tok, rows: list[dict], temp: float = 0.0) -> list[dict]:
    """Generate + judge each eval row (per its `judge` field)."""
    out = []
    for r in rows:
        completion = generate(model, tok, r["system"], r["prompt"], temp=temp)
        spec = {"type": r["type"], "gold": r.get("gold", []),
                "specs": r.get("specs", [])}
        ans, fmt = extract(completion)
        ans = normalize(ans)
        rec = {"id": r["id"], "type": r["type"], "prompt": r["prompt"],
               "completion": completion, "answer": ans, "format": fmt,
               "reference": r["reference"], "judge": r["judge"]}
        if r["judge"].startswith("lean"):
            rb = reward(spec, completion)
            sentence_task = r["type"] != "qa"
            rec["reward"] = rb["reward"]
            rec["task"] = rb["task"]
            rec["grammatical"] = bool(
                sentence_task and ans and check(ans)["grammatical"])
        out.append(rec)
    return out


def summarize(records: list[dict]) -> dict:
    from sacrebleu.metrics import CHRF
    mean = lambda xs: round(sum(xs) / len(xs), 4) if xs else None
    lean_rows = [r for r in records if r["judge"].startswith("lean")]
    sent = [r for r in lean_rows if r["type"] != "qa"]
    qa = [r for r in lean_rows if r["type"] == "qa"]
    chrf = CHRF(word_order=2)  # chrF++, standard settings (nc:6 nw:2 beta:2)
    return {
        "n": len(records),
        "compile_rate": mean([1.0 * r["grammatical"] for r in sent]),
        "qa_exact": mean([1.0 * (r["task"] == 1.0) for r in qa]),
        "mean_reward": mean([r["reward"] for r in lean_rows]),
        "chrf_pp": round(chrf.corpus_score(
            [r["answer"] for r in records],
            [[r["reference"] for r in records]]).score, 2),
    }


def eval_checkpoint(base: str, ckpt: Path | None, rows: list[dict],
                    temp: float = 0.0) -> tuple[dict, list[dict]]:
    adapter = adapter_dir_for(ckpt) if ckpt else None
    model, tok = load_model(base, adapter)
    records = judge_rows(model, tok, rows, temp=temp)
    del model
    return summarize(records), records


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.open()]


def append_jsonl(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
