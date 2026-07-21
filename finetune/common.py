"""Shared pieces: generation, checkpoint evaluation, metrics writing."""

import json
import shutil
import tempfile
import time
from pathlib import Path

from .lean import ROOT, check
from .reward import extract, normalize, reward

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


def adapter_dir_for(checkpoint: Path) -> str:
    """mlx_lm.load wants a dir with adapters.safetensors + adapter_config.json.
    checkpoints/<iteration>/ dirs already have that shape; the file branches
    keep old-layout runs (bare .safetensors) loadable."""
    if checkpoint.is_dir():
        return str(checkpoint)
    if checkpoint.name == "adapters.safetensors":
        return str(checkpoint.parent)
    tmp = Path(tempfile.mkdtemp(prefix="ckpt_"))
    shutil.copy(checkpoint, tmp / "adapters.safetensors")
    shutil.copy(checkpoint.parent / "adapter_config.json", tmp)
    return str(tmp)


def judge_rows(rows: list[dict], completions: list[str]) -> list[dict]:
    """Judge each eval row's completion (per the row's `judge` field).
    Generation is backend-specific and happens before this call."""
    out = []
    for r, completion in zip(rows, completions):
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
    from sacrebleu.metrics import CHRF, TER
    mean = lambda xs: round(sum(xs) / len(xs), 4) if xs else None
    lean_rows = [r for r in records if r["judge"].startswith("lean")]
    sent = [r for r in lean_rows if r["type"] != "qa"]
    qa = [r for r in lean_rows if r["type"] == "qa"]
    hyps = [r["answer"] for r in records]
    refs = [[r["reference"] for r in records]]
    # chrF++ (character n-grams, mildly order-sensitive) and TER (edit rate,
    # lower is better; a block move costs one shift) — read as a pair: high
    # chrF++ with high TER means right words in a different order, which
    # free-word-order Sanskrit permits.
    chrf = CHRF(word_order=2)  # chrF++, standard settings (nc:6 nw:2 beta:2)
    return {
        "n": len(records),
        "compile_rate": mean([1.0 * r["grammatical"] for r in sent]),
        "qa_exact": mean([1.0 * (r["task"] == 1.0) for r in qa]),
        "mean_reward": mean([r["reward"] for r in lean_rows]),
        "chrf_pp": round(chrf.corpus_score(hyps, refs).score, 2),
        "ter": round(TER().corpus_score(hyps, refs).score, 2),
    }


def eval_point(benchmarks: dict[str, list[dict]], generate_rows
               ) -> dict[str, tuple[dict, list[dict]]]:
    """One eval point across every benchmark group. generate_rows(rows) is
    the backend-specific completion source; judging and metrics are shared.
    Returns {group: (summary, records)}."""
    out = {}
    for group, rows in benchmarks.items():
        records = judge_rows(rows, generate_rows(rows))
        out[group] = (summarize(records), records)
    return out


def record_eval_point(run_dir: Path, checkpoint: int, kind: str,
                      results: dict[str, tuple[dict, list[dict]]]) -> dict:
    """Persist one eval point: nested metrics row (one summary object per
    benchmark group) + snapshots/<iteration>/ holding every judged
    generation, mirroring checkpoints/<iteration>/."""
    row = {"checkpoint": checkpoint, "kind": kind}
    snap = run_dir / "snapshots" / str(checkpoint)
    snap.mkdir(parents=True, exist_ok=True)
    for group, (summary, records) in results.items():
        row[group] = summary
        with (snap / f"{group}.jsonl").open("w") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    row["t"] = time.time()
    append_jsonl(run_dir / "metrics.jsonl", row)
    return row


def eval_benchmarks_mlx(base: str, ckpt: Path | None,
                        benchmarks: dict[str, list[dict]], temp: float = 0.0
                        ) -> dict[str, tuple[dict, list[dict]]]:
    """mlx eval point: load base(+adapter) once, judge every benchmark."""
    adapter = adapter_dir_for(ckpt) if ckpt else None
    model, tok = load_model(base, adapter)
    results = eval_point(benchmarks, lambda rows: [
        generate(model, tok, r["system"], r["prompt"], temp=temp)
        for r in rows])
    del model
    return results


def eval_checkpoint(base: str, ckpt: Path | None, rows: list[dict],
                    temp: float = 0.0, backend: str = "mlx",
                    chat_kwargs: dict | None = None
                    ) -> tuple[dict, list[dict]]:
    if backend == "cuda":
        from .cuda_eval import eval_checkpoint_cuda
        return eval_checkpoint_cuda(base, ckpt, rows, temp=temp,
                                    chat_kwargs=chat_kwargs)
    adapter = adapter_dir_for(ckpt) if ckpt else None
    model, tok = load_model(base, adapter)
    completions = [generate(model, tok, r["system"], r["prompt"], temp=temp)
                   for r in rows]
    del model
    records = judge_rows(rows, completions)
    return summarize(records), records


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.open()]


def append_jsonl(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
