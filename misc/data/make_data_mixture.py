#!/usr/bin/env python
"""Assemble data/data-mixture/: the fixed-token-budget mixture experiment set.

Every (token budget x samayik share) arm is trained on a corpus built to an
exact prompt+completion token budget, and every arm (plus the base model) is
evaluated against the SAME two uncontaminated eval files shipped in the folder:

    eval/samayik-eval.json  750 {en,sa} pairs -- byte copy of
                         sft-standard/samayik_validation.json (contamination-
                         group holdout: no train row shares a normalized EN or
                         SA sentence with it). chrF axis, finetune.evals.
    eval/vp-eval.json    669 dhatu tasks -- byte copy of
                         task-data/validation.json (dhatu-level split: no
                         validation root appears in ANY training task, and the
                         Opus R1 traces were rejection-sampled from training
                         tasks only). pass@16 axis, prevals harness.
    val-translation.json 500 rows + ~300 rows (whole tasks) held out of every
    val-morphology.json  mixture: in-training eval-loss probes (checkpoint
                         selection), NOT the reported eval sets above. Duplicate-
                         sentence siblings of val-translation rows and sibling
                         rejection samples of val-morphology tasks are excluded
                         from training too, so the val losses stay unmemorized.
    tb{10,15,20}m/samayik{100,67,50,33,0}.json
                         15 training mixtures, one folder per budget. Samayik
                         token share s of budget
                         B: floor((s*B)/pool) full copies of the translation
                         pool + a seed-42-shuffled remainder prefix (overshoot
                         <= 1 row); same for the R1 trace side at (1-s)*B.
    manifest.json        achieved rows/tokens/shares per file, pool stats,
                         contamination-check results, source-file md5s.

Cleanliness is asserted here, not assumed: the samayik pool is re-checked
against the eval pairs with make_standard_sft_data.norm(), and the trace pool
is re-checked against vp-eval task ids AND dhatu codes. Token counts use the
trainer's exact rendering (finetune.sft.build_text_pairs: Qwen3-4B chat
template, enable_thinking=False, generation-prompt prefix, assistant suffix).

Usage:  uv run --with transformers --with jinja2 python misc/data/make_data_mixture.py
        (transformers is a GPU-box extra; the overlay keeps the local env slim)
"""

import hashlib
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from misc.data.make_standard_sft_data import norm  # noqa: E402

TRANSLATION_SRC = REPO_ROOT / "data" / "finetune" / "sft-standard" / "samayik_finetune.json"
SAMAYIK_EVAL_SRC = REPO_ROOT / "data" / "finetune" / "sft-standard" / "samayik_validation.json"
FLORES_EVAL_SRC = REPO_ROOT / "data" / "eval" / "flores-200.json"  # FULL set: no FLORES rows train
MORPHOLOGY_SRC = REPO_ROOT / "data" / "finetune" / "sft-r1" / "claude-opus-5.json"
VP_EVAL_SRC = REPO_ROOT / "data" / "finetune" / "task-data" / "validation.json"
OUT_DIR = REPO_ROOT / "data" / "data-mixture"

TOKENIZER = "Qwen/Qwen3-4B"
BUDGETS = {"10m": 10_000_000, "15m": 15_000_000, "20m": 20_000_000}
SAMAYIK_SHARES = (100, 67, 50, 33, 0)   # % of the token budget, prompt+completion
N_VAL_TRANSLATION = 500
N_VAL_MORPHOLOGY = 300
SEED = 42
_SENTINEL = "\x00mixture-sentinel\x00"


def token_counts(tokenizer, records: list[dict]) -> list[int]:
    """Prompt+completion tokens per record, exactly as finetune.sft renders them.

    The chat template is probed once with a sentinel (same trick as
    build_text_pairs) so 55k records need string splices, not 55k jinja runs;
    the probe-based render is asserted equal to a real apply_chat_template."""
    gen = tokenizer.apply_chat_template(
        [{"role": "user", "content": _SENTINEL}],
        tokenize=False, add_generation_prompt=True, enable_thinking=False)
    head, tail = gen.split(_SENTINEL, 1)
    full = tokenizer.apply_chat_template(
        [{"role": "user", "content": "x"}, {"role": "assistant", "content": _SENTINEL}],
        tokenize=False, enable_thinking=False)
    suffix = full.split(_SENTINEL, 1)[1]

    def render(r: dict) -> str:
        return (head + r["prompt"][0]["content"] + tail
                + r["completion"][0]["content"] + suffix)

    r0 = records[0]
    direct = (tokenizer.apply_chat_template(
                  r0["prompt"], tokenize=False, add_generation_prompt=True,
                  enable_thinking=False)
              + r0["completion"][0]["content"] + suffix)
    assert render(r0) == direct, "sentinel render diverged from apply_chat_template"
    return [len(ids) for ids in tokenizer([render(r) for r in records])["input_ids"]]


def slim(record: dict, task: str) -> dict:
    return {"id": record["id"], "task": task,
            "prompt": record["prompt"], "completion": record["completion"]}


def fill_to_target(rows: list[dict], counts: list[int], target: int):
    """Whole-pool copies then a seed-42-shuffled remainder prefix; returns
    (rows, achieved_tokens). Overshoot is at most one record."""
    if target <= 0:
        return [], 0
    pool_total = sum(counts)
    copies = target // pool_total
    out = [r for _ in range(copies) for r in rows]
    achieved = copies * pool_total
    if achieved < target:
        order = random.Random(SEED).sample(range(len(rows)), len(rows))
        for i in order:
            if achieved >= target:
                break
            out.append(rows[i])
            achieved += counts[i]
    return out, achieved


def write_json(path: Path, rows) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
        f.write("\n")


def copy_with_md5(src: Path, dst: Path) -> str:
    data = src.read_bytes()
    dst.write_bytes(data)
    return hashlib.md5(data).hexdigest()


def main() -> None:
    from transformers import AutoTokenizer

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    trans = json.loads(TRANSLATION_SRC.read_text())
    morph = json.loads(MORPHOLOGY_SRC.read_text())
    samayik_eval = json.loads(SAMAYIK_EVAL_SRC.read_text())
    vp_eval = json.loads(VP_EVAL_SRC.read_text())

    # --- contamination asserts: the guarantees this folder exists to provide ---
    eval_en = {norm(p["en"]) for p in samayik_eval}
    eval_sa = {norm(p["sa"]) for p in samayik_eval}
    dirty = [r["id"] for r in trans
             if norm(r["en"]) in eval_en or norm(r["sa"]) in eval_sa]
    assert not dirty, f"samayik train rows share a sentence with the eval set: {dirty[:5]}"

    vp_ids = {t["id"] for t in vp_eval}
    vp_dhatus = {t["dhatu"]["code"] for t in vp_eval}
    leaked_ids = {r["id"] for r in morph} & vp_ids
    leaked_dhatus = {r["dhatu"]["code"] for r in morph} & vp_dhatus
    assert not leaked_ids and not leaked_dhatus, \
        f"R1 traces overlap vp-eval: ids={sorted(leaked_ids)[:5]} dhatus={sorted(leaked_dhatus)[:5]}"
    print(f"contamination checks: samayik 0/{len(trans)} rows dirty; "
          f"traces 0/{len(morph)} overlap vp-eval ({len(vp_dhatus)} held-out dhatus)",
          file=sys.stderr)

    # --- token accounting in trainer units --------------------------------
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER)
    trans_tok = token_counts(tokenizer, trans)
    morph_tok = token_counts(tokenizer, morph)

    # --- fixed eval-loss holdouts, carved before any mixing ----------------
    # Translation: 500 rows, PLUS every pool row sharing a normalized EN or SA
    # sentence with a held-out row (duplicate sentences would otherwise let the
    # trainer memorize the val loss) -- the same guarantee the real eval set
    # gets from make_standard_sft_data.
    rng = random.Random(SEED)
    val_t = set(rng.sample(range(len(trans)), N_VAL_TRANSLATION))
    vt_en = {norm(trans[i]["en"]) for i in val_t}
    vt_sa = {norm(trans[i]["sa"]) for i in val_t}
    sib_t = {i for i, r in enumerate(trans) if i not in val_t
             and (norm(r["en"]) in vt_en or norm(r["sa"]) in vt_sa)}
    # Morphology: trace ids are TASK ids (~2 rejection samples per task), so
    # hold out whole tasks -- a val trace's sibling sample must not stay in
    # training with a near-identical derivation.
    by_task = defaultdict(list)
    for i, r in enumerate(morph):
        by_task[r["id"]].append(i)
    task_order = sorted(by_task)
    rng.shuffle(task_order)
    val_m, val_m_tasks = set(), []
    for t in task_order:
        if len(val_m) >= N_VAL_MORPHOLOGY:
            break
        val_m_tasks.append(t)
        val_m.update(by_task[t])

    write_json(OUT_DIR / "val-translation.json",
               [slim(trans[i], "translation") for i in sorted(val_t)])
    write_json(OUT_DIR / "val-morphology.json",
               [slim(morph[i], "morphology") for i in sorted(val_m)])
    print(f"val holdouts: {len(val_t)} translation rows (+{len(sib_t)} duplicate-"
          f"sentence siblings excluded from training) | {len(val_m)} morphology "
          f"rows = {len(val_m_tasks)} whole tasks", file=sys.stderr)

    pool_t = [(slim(r, "translation"), c) for i, (r, c) in enumerate(zip(trans, trans_tok))
              if i not in val_t and i not in sib_t]
    pool_m = [(slim(r, "morphology"), c) for i, (r, c) in enumerate(zip(morph, morph_tok))
              if i not in val_m]
    rows_t, counts_t = [list(x) for x in zip(*pool_t)]
    rows_m, counts_m = [list(x) for x in zip(*pool_m)]
    print(f"train pools: {len(rows_t)} translation rows = {sum(counts_t):,} tokens | "
          f"{len(rows_m)} morphology rows = {sum(counts_m):,} tokens", file=sys.stderr)

    # --- one corpus per (budget, samayik share) ----------------------------
    manifest = {
        "tokenizer": TOKENIZER,
        "token_definition": "prompt+completion, finetune.sft.build_text_pairs rendering",
        "seed": SEED,
        "sources": {
            "translation_pool": str(TRANSLATION_SRC.relative_to(REPO_ROOT)),
            "morphology_pool": str(MORPHOLOGY_SRC.relative_to(REPO_ROOT)),
        },
        "pools": {
            "translation": {"rows": len(rows_t), "tokens": sum(counts_t)},
            "morphology": {"rows": len(rows_m), "tokens": sum(counts_m)},
        },
        "val_holdouts": {
            "translation": {
                "rows": len(val_t), "sibling_rows_excluded": len(sib_t),
                "excluded_ids": sorted(trans[i]["id"] for i in val_t | sib_t),
            },
            "morphology": {
                "rows": len(val_m), "tasks": len(val_m_tasks),
                "task_ids": sorted(val_m_tasks),
            },
        },
        "contamination_checks": {
            "samayik_train_rows_sharing_eval_sentence": 0,
            "trace_task_ids_in_vp_eval": 0,
            "trace_dhatus_in_vp_eval": 0,
        },
        "files": {},
    }

    for bname, budget in BUDGETS.items():
        budget_dir = OUT_DIR / f"tb{bname}"
        budget_dir.mkdir(exist_ok=True)
        for pct in SAMAYIK_SHARES:
            target_t = round(budget * pct / 100)
            mix_t, got_t = fill_to_target(rows_t, counts_t, target_t)
            mix_m, got_m = fill_to_target(rows_m, counts_m, budget - target_t)
            rows = mix_t + mix_m
            random.Random(SEED).shuffle(rows)
            assert all(len(r["prompt"]) == 1 and r["prompt"][0]["role"] == "user"
                       and len(r["completion"]) == 1
                       and r["completion"][0]["role"] == "assistant" for r in rows)

            name = f"tb{bname}/samayik{pct}.json"
            write_json(budget_dir / f"samayik{pct}.json", rows)
            total = got_t + got_m
            manifest["files"][name] = {
                "budget": budget, "samayik_share_target": pct / 100,
                "rows": len(rows), "tokens": total,
                "samayik_tokens": got_t, "morphology_tokens": got_m,
                "samayik_share_achieved": round(got_t / total, 4),
                "upsample_translation": round(got_t / sum(counts_t), 3),
                "upsample_morphology": round(got_m / sum(counts_m), 3),
            }
            print(f"{name}: {len(rows):>7,} rows  {total:>10,} tokens "
                  f"({got_t / total:6.1%} samayik, overshoot {total - budget:>4} tok)",
                  file=sys.stderr)

    # --- eval files: byte copies so existing tooling numbers apply verbatim ---
    (OUT_DIR / "eval").mkdir(exist_ok=True)
    manifest["eval_files"] = {
        "eval/samayik-eval.json": {
            "source": str(SAMAYIK_EVAL_SRC.relative_to(REPO_ROOT)),
            "md5": copy_with_md5(SAMAYIK_EVAL_SRC, OUT_DIR / "eval" / "samayik-eval.json"),
            "pairs": len(samayik_eval),
        },
        "eval/vp-eval.json": {
            "source": str(VP_EVAL_SRC.relative_to(REPO_ROOT)),
            "md5": copy_with_md5(VP_EVAL_SRC, OUT_DIR / "eval" / "vp-eval.json"),
            "tasks": len(vp_eval),
        },
        "eval/flores-200.json": {
            "source": str(FLORES_EVAL_SRC.relative_to(REPO_ROOT)),
            "md5": copy_with_md5(FLORES_EVAL_SRC, OUT_DIR / "eval" / "flores-200.json"),
            "pairs": len(json.loads(FLORES_EVAL_SRC.read_text())),
        },
    }
    write_json(OUT_DIR / "manifest.json", manifest)
    print(f"wrote {len(manifest['files'])} mixtures + 2 eval files + 2 val holdouts "
          f"+ manifest -> {OUT_DIR.relative_to(REPO_ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
