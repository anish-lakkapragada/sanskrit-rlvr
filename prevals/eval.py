"""Base-capability sweep: pass@k on the dhatu morphology task for a list of
candidate models. Scoring is imported from finetune.* (same prompt template,
same reward registry, same pass@k estimator), so numbers here are directly
comparable to training-time evals in runs/*/evals/.

Usage (repo root):
    uv run python -m prevals.eval prevals/outputs/configs/v1/eval-config.yml              # full sweep (GPU)
    uv run python -m prevals.eval prevals/outputs/configs/v1/eval-config.yml --dry-run    # validate config, no GPU
    uv run python -m prevals.eval prevals/outputs/configs/v1/eval-config.yml --self-test  # CPU end-to-end, stub generator

Each model runs in its OWN subprocess (--model-index, internal): vLLM does not
reliably release GPU memory on engine teardown, so sequential engines in one
process OOM by the second model on a 40GB card.

Models with ``backend: anthropic`` (Claude, e.g. configs/v1/eval-config-claude.yml)
skip vLLM entirely and generate over the Anthropic Message Batches API in-process
(needs ANTHROPIC_API_KEY in the environment or repo-root .env); scoring and
reports are identical.

Per model, under <report.output_dir>/<suite_name>/<model_slug>/:
    results.txt    human-readable report (pass@k + CI, compliance, timing, screen)
    samples.json   [{"input_task", "prompt", "outputs" (raw completion text, all
                   n tries), "output_devanagari", "exact_answers"}, ...]
    summary.json   machine-readable metrics, aggregated into the final table
"""

import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np
import yaml

from finetune.config import ROOT
from finetune.data import load_vp_tasks
from finetune.evals import pass_at_k_estimate, reward_snapshot
from finetune.model import resolve_model_id
from finetune.prompts import PROMPT_VERSION, extract_answer, render_vp_task
from finetune.rewards import get as get_reward

_THINKING_RE = re.compile(r"<thinking>(.*?)</thinking>", re.DOTALL)
BOOTSTRAP_RESAMPLES = 10_000


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

def slugify(name: str) -> str:
    """HF id -> directory name. Keeps the org so same-named models from
    different orgs cannot collide: Qwen/Qwen3-4B -> qwen__qwen3-4b."""
    return name.replace("/", "__").lower()


def load_suite(path: str | Path) -> dict:
    cfg = yaml.safe_load(Path(path).read_text())
    pk = cfg["pass_at_k"]
    pk["ks"] = sorted(pk["ks"])
    if max(pk["ks"]) > pk["samples_per_prompt"]:
        raise ValueError(
            f"max k={max(pk['ks'])} > samples_per_prompt={pk['samples_per_prompt']}")
    get_reward(cfg["task"]["reward"])  # fail fast on unknown reward
    if not (ROOT / cfg["task"]["dataset"]).exists():
        raise FileNotFoundError(cfg["task"]["dataset"])
    if not cfg.get("models"):
        raise ValueError("config has no models")
    defaults = cfg.get("defaults") or {}
    cfg["models"] = [{**defaults, **m} for m in cfg["models"]]
    return cfg


def choose_tasks(cfg: dict) -> tuple[list[dict], int]:
    """Seeded ONCE from the suite seed: every model sees the same prompts."""
    tasks = load_vp_tasks(cfg["task"]["dataset"])
    rng = random.Random(cfg["seed"])
    n = min(cfg["pass_at_k"]["num_prompts"], len(tasks))
    return rng.sample(tasks, n), len(tasks)


def task_template(cfg: dict) -> str:
    """prompts/*.txt filename from the config (vp_task_eval.txt has the
    few-shot worked examples baked in)."""
    return cfg["task"].get("prompt", "vp_task") + ".txt"


# --------------------------------------------------------------------------
# Generation. records[prompt_i][sample_j] = {text, tokens, truncated}
# --------------------------------------------------------------------------

def generate_vllm(model_cfg: dict, prompts: list[str], pk: dict, seed: int):
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    model_id = resolve_model_id(model_cfg["name"])
    t0 = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(
        model_id, trust_remote_code=model_cfg["trust_remote_code"])
    # Base models (e.g. buddhist-nlp/gemma2-mitra-base) have no chat template;
    # transformers 5.x raises rather than falling back to a default. Honor an
    # explicit chat: false, and auto-detect the template-less case.
    raw = not model_cfg.get("chat", True) or tokenizer.chat_template is None
    if raw:
        print(f"[eval] {model_cfg['name']}: no chat template -> raw completion mode")
        texts = list(prompts)
    else:
        # enable_thinking is a template variable: honored by templates that have
        # the toggle (Qwen3), silently ignored by those that don't (gemma, llama).
        texts = [
            tokenizer.apply_chat_template(
                [{"role": "user", "content": p}],
                tokenize=False, add_generation_prompt=True,
                enable_thinking=model_cfg["enable_thinking"],
            )
            for p in prompts
        ]

    lora_kwargs, lora_request = {}, None
    if model_cfg.get("adapter"):
        from vllm.lora.request import LoRARequest

        adapter_dir = ROOT / model_cfg["adapter"]
        # vLLM's default max_lora_rank is 16; size it to the adapter's actual r.
        rank = json.loads((adapter_dir / "adapter_config.json").read_text()).get("r", 16)
        lora_kwargs = {"enable_lora": True, "max_lora_rank": max(rank, 16)}
        lora_request = LoRARequest("adapter", 1, str(adapter_dir))

    llm = LLM(
        model=model_id,
        dtype=model_cfg["dtype"],
        max_model_len=model_cfg["max_model_len"],
        gpu_memory_utilization=model_cfg["gpu_memory_utilization"],
        tensor_parallel_size=model_cfg["tensor_parallel_size"],
        trust_remote_code=model_cfg["trust_remote_code"],
        **lora_kwargs,
    )
    load_s = time.perf_counter() - t0

    # Raw mode: base models have no "end of turn" -- without a stop string they
    # run to max_new_tokens after answering (and may emit a second imitation
    # block, which makes extract_answer's exactly-one check fail).
    stop_kwargs = ({"stop": ["</answer>"], "include_stop_str_in_output": True}
                   if raw else {})
    params = SamplingParams(
        n=pk["samples_per_prompt"],
        temperature=max(pk["temperature"], 1e-6),
        top_p=pk.get("top_p", 1.0),
        max_tokens=model_cfg["max_new_tokens"],
        seed=seed,
        **stop_kwargs,
    )
    t1 = time.perf_counter()
    outs = llm.generate(texts, params, lora_request=lora_request)
    gen_s = time.perf_counter() - t1

    records = [
        [{"text": o.text, "tokens": len(o.token_ids),
          "truncated": o.finish_reason == "length"} for o in out.outputs]
        for out in outs
    ]
    import torch
    import vllm

    device = (torch.cuda.get_device_name(0)
              if torch.cuda.is_available() else "cpu")
    return records, {"load_s": load_s, "gen_s": gen_s,
                     "device": device, "engine": f"vllm {vllm.__version__}"}


def _anthropic_api_key() -> str | None:
    """ANTHROPIC_API_KEY from the environment, falling back to ROOT/.env."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY"):
                return line.split("=", 1)[1].strip().strip("'\"") or None
    return None


def generate_anthropic(model_cfg: dict, prompts: list[str], pk: dict, seed: int):
    """Claude models (backend: anthropic) over the Message Batches API --
    50% of standard token prices, no rate-limit wrangling for the
    prompts x samples fan-out.

    Protocol differences vs generate_vllm, forced by the API:
    - no temperature/top_p/seed: current Claude models reject sampling
      params, so the n samples per prompt vary only via default sampling
      (`seed` is accepted for signature parity and unused)
    - anthropic_thinking: 'disabled' sends thinking={'type': 'disabled'}
      (opus-5/sonnet-5 otherwise think by default), 'adaptive' opts in,
      'omit' sends nothing (haiku-4-5 rejects the disabled type). The
      prompt-demanded in-text <thinking> block is unaffected.
    - refused (stop_reason 'refusal') or errored requests score as empty
      completions (reward 0); counts are printed.
    """
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    api_key = _anthropic_api_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set (environment or .env)")
    client = anthropic.Anthropic(api_key=api_key)

    n = pk["samples_per_prompt"]
    thinking_mode = model_cfg.get("anthropic_thinking", "omit")
    if thinking_mode not in ("omit", "disabled", "adaptive"):
        raise ValueError(f"anthropic_thinking must be omit|disabled|adaptive, "
                         f"got {thinking_mode!r}")
    extra = ({} if thinking_mode == "omit"
             else {"thinking": {"type": thinking_mode}})

    t0 = time.perf_counter()
    requests = [
        Request(
            custom_id=f"p{i}-s{j}",
            params=MessageCreateParamsNonStreaming(
                model=model_cfg["name"],
                max_tokens=model_cfg["max_new_tokens"],
                messages=[{"role": "user", "content": prompt}],
                **extra,
            ),
        )
        for i, prompt in enumerate(prompts)
        for j in range(n)
    ]
    batch = client.messages.batches.create(requests=requests)
    print(f"[eval] {model_cfg['name']}: batch {batch.id} "
          f"({len(requests)} requests) submitted; polling every 30s...")
    while True:
        batch = client.messages.batches.retrieve(batch.id)
        if batch.processing_status == "ended":
            break
        c = batch.request_counts
        print(f"[eval]   {batch.processing_status}: {c.succeeded} ok, "
              f"{c.errored} errored, {c.processing} left "
              f"({time.perf_counter() - t0:.0f}s)", flush=True)
        time.sleep(30)

    by_id, refusals, failures = {}, 0, 0
    for result in client.messages.batches.results(batch.id):
        if result.result.type == "succeeded":
            msg = result.result.message
            if msg.stop_reason == "refusal":
                refusals += 1
            by_id[result.custom_id] = {
                "text": "".join(b.text for b in msg.content if b.type == "text"),
                "tokens": msg.usage.output_tokens,
                "truncated": msg.stop_reason == "max_tokens",
            }
        else:
            failures += 1
    gen_s = time.perf_counter() - t0
    if refusals or failures:
        print(f"[eval] {model_cfg['name']}: {refusals} refusals, {failures} "
              f"errored/expired requests -- scored as empty completions")

    empty = {"text": "", "tokens": 0, "truncated": False}
    records = [[dict(by_id.get(f"p{i}-s{j}", empty)) for j in range(n)]
               for i in range(len(prompts))]
    return records, {"load_s": 0.0, "gen_s": gen_s,
                     "device": "anthropic-batches-api",
                     "engine": f"anthropic {anthropic.__version__}"}


# --------------------------------------------------------------------------
# Scoring (mirrors finetune.evals.eval_pass_at_k, plus per-sample structure,
# truncation stats, and a bootstrap CI)
# --------------------------------------------------------------------------

def score(cfg: dict, tasks: list[dict], prompts: list[str], records):
    pk = cfg["pass_at_k"]
    reward_fn = get_reward(cfg["task"]["reward"])

    # One flat reward call, mirroring TRL's batching.
    flat_prompts, flat_texts, cols = [], [], {
        "id": [], "dhatu": [], "morphology": [],
        "gold_slp1": [], "gold_devanagari": [],
    }
    for task, prompt, recs in zip(tasks, prompts, records):
        for r in recs:
            flat_prompts.append(prompt)
            flat_texts.append(r["text"])
            for key in cols:
                cols[key].append(task[key])
    flat_rewards = reward_fn(flat_prompts, flat_texts, **cols)

    def nfc(s):
        return unicodedata.normalize("NFC", s)

    # Two per-task correct-counts, same estimator downstream:
    #   pass:  reward >= threshold (tag-extracted exact match; what training sees)
    #   exact: a gold form appears ANYWHERE in the text (format-blind; the gold
    #          never appears in the prompt's task section, so a hit is signal)
    counts = {"pass": [], "exact": []}
    sample_rows, i = [], 0
    for task, prompt, recs in zip(tasks, prompts, records):
        rewards = flat_rewards[i:i + len(recs)]
        i += len(recs)
        passed = [r is not None and r >= pk["pass_threshold"] for r in rewards]
        golds = [nfc(g) for g in task["gold_devanagari"]]
        anywhere = [any(g in nfc(r["text"]) for g in golds) for r in recs]
        counts["pass"].append((len(recs), sum(passed)))
        counts["exact"].append((len(recs), sum(anywhere)))
        sample_rows.append({
            "input_task": task,
            "prompt": prompt,                      # rendered task prompt (pre chat template)
            "outputs": [r["text"] for r in recs],  # raw completion text, all n tries
            "output_devanagari": [extract_answer(r["text"]) for r in recs],
            "exact_answers": passed,
        })

    # 95% CI: bootstrap over prompts (the unit of variation that matters here).
    # The same resample indices pair the two metrics.
    ks = pk["ks"]
    rng = np.random.default_rng(cfg["seed"])
    idx = rng.integers(0, len(tasks), size=(BOOTSTRAP_RESAMPLES, len(tasks)))
    kstats = {}
    for name, per_task in counts.items():
        per_k = np.array([[pass_at_k_estimate(n, c, k) for k in ks]
                          for n, c in per_task])
        boot = per_k[idx].mean(axis=1)
        kstats[name] = {
            "at": {k: float(per_k[:, j].mean()) for j, k in enumerate(ks)},
            "ci": {k: (float(np.percentile(boot[:, j], 2.5)),
                       float(np.percentile(boot[:, j], 97.5)))
                   for j, k in enumerate(ks)},
            "solved": int(sum(1 for _, c in per_task if c > 0)),
            "hits": int(sum(c for _, c in per_task)),
        }

    flat_recs = [r for recs in records for r in recs]
    tokens = np.array([r["tokens"] for r in flat_recs])
    misc = {
        "answer_tag_rate": float(np.mean(
            [extract_answer(t) is not None for t in flat_texts])),
        "thinking_tag_rate": float(np.mean(
            [len(_THINKING_RE.findall(t)) == 1 for t in flat_texts])),
        "truncated": int(sum(r["truncated"] for r in flat_recs)),
        "completions": len(flat_recs),
        "total_tokens": int(tokens.sum()),
        "mean_tokens": float(tokens.mean()),
        "min_tokens": int(tokens.min()),
        "max_tokens": int(tokens.max()),
        "reward_snapshot": reward_snapshot(flat_rewards),
    }
    return kstats, misc, sample_rows


def param_count_b(model_id: str) -> float | None:
    """Total params in billions from hub safetensors metadata (no download).
    None when offline / gated / metadata missing."""
    try:
        from huggingface_hub import model_info

        total = model_info(model_id).safetensors.total
        return total / 1e9 if total else None
    except Exception:
        return None


def selection_screen(cfg, kstats, misc, params_b, api_model=False):
    """[(True|False|None, criterion, observed), ...] -- None = not measurable.
    API models are capability reference points, not SFT-base candidates, so
    they skip the train-run row (and usually the whole selection block)."""
    sel = cfg.get("selection") or {}
    rows = []
    if "min_pass_at_8" in sel and 8 in kstats["pass"]["at"]:
        v = kstats["pass"]["at"][8]
        rows.append((v >= sel["min_pass_at_8"],
                     f"pass@8 >= {sel['min_pass_at_8']}", f"{v:.4f}"))
    if "min_answer_tag_rate" in sel:
        v = misc["answer_tag_rate"]
        rows.append((v >= sel["min_answer_tag_rate"],
                     f"answer_tag_rate >= {sel['min_answer_tag_rate']}", f"{v:.4f}"))
    if "max_params_b" in sel:
        ok = None if params_b is None else params_b <= sel["max_params_b"]
        rows.append((ok, f"params <= {sel['max_params_b']}B",
                     "unknown" if params_b is None else f"{params_b:.1f}B"))
    if not api_model:
        rows.append((None,
                     f"{sel.get('target_steps', 100)} steps in <= "
                     f"{sel.get('target_minutes', 10)} min",
                     "not measurable from eval -- needs a train run"))
    return rows


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

def _dur(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}m {s:02d}s" if m else f"{s}s"


def _k_table(title, label, ks, stat, num_prompts, completions, notes) -> list[str]:
    """One pass@k-style table: k / value / bootstrap CI / solved-at-max-k."""
    thin = "-" * 80
    L = ["", thin, f" {title}", thin,
         f" {'k':>6}   {label + '@k':>9}   {'95% CI':^20}   {'solved':>10}",
         f" {'-----':>6}   {'-' * 9}   {'-' * 20}   {'-' * 10}"]
    for k in ks:
        v, (lo, hi) = stat["at"][k], stat["ci"][k]
        solved = f"{stat['solved']:>3} / {num_prompts}" if k == max(ks) else "-"
        L.append(f" {k:>6}   {v * 100:>8.2f}%   [{lo * 100:>6.2f}%, "
                 f"{hi * 100:>7.2f}%]   {solved:>10}")
    p1, pmax = stat["at"][ks[0]], stat["at"][max(ks)]
    L += ["",
          f"  headroom  {label}@{max(ks)} / {label}@{ks[0]} = "
          + (f"{pmax / p1:.1f}x" if p1 > 0 else f"n/a ({label}@{ks[0]} = 0)"),
          f"  hits  {stat['hits']} / {completions} completions "
          f"({stat['hits'] / completions * 100:.2f}%)"]
    return L + notes


def format_report(cfg, model_cfg, kstats, misc, timing,
                  params_b, screen, dataset_n, num_prompts) -> str:
    pk = cfg["pass_at_k"]
    n = pk["samples_per_prompt"]
    rule, thin = "=" * 80, "-" * 80
    L = [rule,
         f" vp_exact base capability -- {model_cfg['name']}",
         rule,
         f" suite          {cfg['suite_name']}",
         f" model          {resolve_model_id(model_cfg['name'])}"
         + (f"   adapter={model_cfg['adapter']}" if model_cfg.get("adapter")
            else "   (base, no adapter)"),
         f" reward         {cfg['task']['reward']}  (pass iff >= {pk['pass_threshold']})",
         f" dataset        {cfg['task']['dataset']}   ({dataset_n} held-out tasks)",
         f" prompt         {task_template(cfg)}  v{PROMPT_VERSION}"
         f"   enable_thinking={model_cfg['enable_thinking']}"
         f"  chat={model_cfg.get('chat', True)}",
         f" sampling       temperature={pk['temperature']}  top_p={pk.get('top_p', 1.0)}"
         f"  max_new_tokens={model_cfg['max_new_tokens']}",
         f" subset         {num_prompts} prompts x {n} samples = "
         f"{num_prompts * n} completions   seed={cfg['seed']}",
         f" run            {time.strftime('%Y-%m-%d %H:%M:%S')}   "
         f"{timing['device']}   {timing['engine']}"]
    L += _k_table("PASS@K  (tag-extracted answer -- what training rewards)",
                  "pass", pk["ks"], kstats["pass"], num_prompts,
                  misc["completions"],
                  ["  unbiased estimator (Chen et al. 2021); "
                   f"CI = {BOOTSTRAP_RESAMPLES // 1000}k-resample bootstrap over prompts"])
    L += _k_table("EXACT@K  (gold form anywhere in the text -- format-blind)",
                  "exact", pk["ks"], kstats["exact"], num_prompts,
                  misc["completions"],
                  ["  a large EXACT-over-PASS gap = knows the Sanskrit, fails the format"])
    L += ["", thin, " FORMAT COMPLIANCE", thin,
          f" answer_tag_rate           {misc['answer_tag_rate'] * 100:5.1f}%",
          f" thinking_tag_rate         {misc['thinking_tag_rate'] * 100:5.1f}%",
          f" hit max_new_tokens        {misc['truncated'] / misc['completions'] * 100:5.1f}%"
          f"    ({misc['truncated']} / {misc['completions']} truncated)",
          f" mean completion length    {misc['mean_tokens']:5.0f} tokens"
          f"   (min {misc['min_tokens']}, max {misc['max_tokens']})",
          "", thin, " REWARD DISTRIBUTION", thin]
    snap = misc["reward_snapshot"]
    L.append(f" mean {snap['mean']:.4f}   std {snap['std']:.4f}   "
             f"min {snap['min']:.3f}   max {snap['max']:.3f}")
    L.append("")
    peak = max(snap["hist_counts"]) or 1
    for left, count in zip(snap["hist_bins"], snap["hist_counts"]):
        if count:
            L.append(f"   {left:5.2f}  |{'#' * max(1, round(48 * count / peak)):<48}"
                     f"  {count}")
    tot = timing["load_s"] + timing["gen_s"]
    gen_s = max(timing["gen_s"], 1e-9)
    L += ["", thin, " TIMING", thin,
          f" avg inference time / prompt       {gen_s / num_prompts:6.2f} s"
          f"      ({n} completions per prompt)",
          f" avg inference time / completion   {gen_s / (num_prompts * n):6.2f} s",
          f" output throughput                 {misc['total_tokens'] / gen_s:6.0f} tok/s",
          f" total generation wall clock       {_dur(timing['gen_s']):>7}",
          f" model load + engine init          {_dur(timing['load_s']):>7}",
          f" total wall clock                  {_dur(tot):>7}",
          "", thin, " SELECTION SCREEN", thin]
    for ok, crit, obs in screen:
        mark = {True: "[PASS]", False: "[FAIL]", None: "[ ? ]"}[ok]
        L.append(f" {mark:<6}  {crit:<28} {obs}")
    L.append(rule)
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------
# Single-model run (the unit of work; also the --self-test entry)
# --------------------------------------------------------------------------

def run_one(cfg, index, generate_fn=None, subdir=None, lookup_params=True):
    model_cfg = cfg["models"][index]
    api_model = model_cfg.get("backend", "vllm") == "anthropic"
    tasks, dataset_n = choose_tasks(cfg)
    prompts = [render_vp_task(t, template=task_template(cfg)) for t in tasks]

    generate = generate_fn or (generate_anthropic if api_model else generate_vllm)
    records, timing = generate(model_cfg, prompts, cfg["pass_at_k"], cfg["seed"])
    kstats, misc, sample_rows = score(cfg, tasks, prompts, records)

    params_b = (param_count_b(resolve_model_id(model_cfg["name"]))
                if lookup_params and not api_model else None)
    screen = selection_screen(cfg, kstats, misc, params_b, api_model=api_model)
    known = [ok for ok, _, _ in screen if ok is not None]
    gen_s = max(timing["gen_s"], 1e-9)

    out_dir = (ROOT / cfg["report"]["output_dir"]
               / (subdir or cfg["suite_name"]) / slugify(model_cfg["name"]))
    out_dir.mkdir(parents=True, exist_ok=True)

    report = format_report(cfg, model_cfg, kstats, misc, timing,
                           params_b, screen, dataset_n, len(prompts))
    (out_dir / "results.txt").write_text(report)
    if cfg["report"].get("save_samples", True):
        (out_dir / "samples.json").write_text(
            json.dumps(sample_rows, ensure_ascii=False, indent=1))

    summary = {
        "model": model_cfg["name"],
        "resolved_id": resolve_model_id(model_cfg["name"]),
        "adapter": model_cfg.get("adapter"),
        "params_b": params_b,
        "chat": model_cfg.get("chat", True),
        "pass_at_k": {str(k): kstats["pass"]["at"][k] for k in cfg["pass_at_k"]["ks"]},
        "exact_at_k": {str(k): kstats["exact"]["at"][k] for k in cfg["pass_at_k"]["ks"]},
        "ci95_pass": {str(k): kstats["pass"]["ci"][k] for k in cfg["pass_at_k"]["ks"]},
        "ci95_exact": {str(k): kstats["exact"]["ci"][k] for k in cfg["pass_at_k"]["ks"]},
        "answer_tag_rate": misc["answer_tag_rate"],
        "thinking_tag_rate": misc["thinking_tag_rate"],
        "truncated_frac": misc["truncated"] / misc["completions"],
        "mean_tokens": misc["mean_tokens"],
        "solved_tasks": kstats["pass"]["solved"],
        "solved_tasks_exact": kstats["exact"]["solved"],
        "num_prompts": len(prompts),
        "samples_per_prompt": cfg["pass_at_k"]["samples_per_prompt"],
        "timing": {
            "load_s": timing["load_s"], "gen_s": timing["gen_s"],
            "s_per_prompt": gen_s / len(prompts),
            "s_per_completion": gen_s / misc["completions"],
            "output_tok_s": misc["total_tokens"] / gen_s,
        },
        "screen_passed": all(known) if known else None,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    print(report)
    print(f"[eval] wrote {out_dir}/")
    return summary, out_dir


# --------------------------------------------------------------------------
# Sweep orchestration
# --------------------------------------------------------------------------

def print_comparison(cfg):
    ks = cfg["pass_at_k"]["ks"]
    kmax = max(ks)
    head = (f" {'model':<38} {'params':>7} {'pass@1':>8} {f'pass@{kmax}':>9}"
            f" {f'exact@{kmax}':>10} {'tag%':>6} {'s/prompt':>9} {'tok/s':>7}  screen")
    print("\n" + "=" * len(head) + f"\n {cfg['suite_name']}\n" + head + "\n" + "-" * len(head))
    for m in cfg["models"]:
        path = (ROOT / cfg["report"]["output_dir"] / cfg["suite_name"]
                / slugify(m["name"]) / "summary.json")
        if not path.exists():
            print(f" {m['name']:<38} {'-':>7} {'FAILED (no summary.json)':>25}")
            continue
        s = json.loads(path.read_text())
        params = f"{s['params_b']:.1f}B" if s["params_b"] else "?"
        screen = {True: "PASS", False: "FAIL", None: "?"}[s["screen_passed"]]
        print(f" {m['name']:<38} {params:>7}"
              f" {s['pass_at_k']['1'] * 100:>7.2f}%"
              f" {s['pass_at_k'][str(kmax)] * 100:>8.2f}%"
              f" {s['exact_at_k'][str(kmax)] * 100:>9.2f}%"
              f" {s['answer_tag_rate'] * 100:>5.1f}%"
              f" {s['timing']['s_per_prompt']:>8.2f}s"
              f" {s['timing']['output_tok_s']:>7.0f}  {screen}")
    print("=" * len(head))


def sweep(cfg, config_path):
    fail_fast = cfg["report"].get("fail_fast", False)
    for i, m in enumerate(cfg["models"]):
        print(f"\n[sweep] ({i + 1}/{len(cfg['models'])}) {m['name']}", flush=True)
        if m.get("backend", "vllm") == "anthropic":
            # No GPU engine to tear down -> no need for subprocess isolation.
            try:
                run_one(cfg, i)
            except Exception as e:
                print(f"[sweep] {m['name']} FAILED ({e})"
                      + ("" if fail_fast else "; continuing"))
                if fail_fast:
                    raise
            continue
        rc = subprocess.call(
            [sys.executable, "-m", "prevals.eval", str(config_path),
             "--model-index", str(i)],
            cwd=ROOT)
        if rc != 0:
            print(f"[sweep] {m['name']} FAILED (rc={rc})"
                  + ("" if fail_fast else "; continuing"))
            if fail_fast:
                sys.exit(rc)
    if cfg["report"].get("print_table", True):
        print_comparison(cfg)


# --------------------------------------------------------------------------
# Dry run + CPU self-test
# --------------------------------------------------------------------------

def dry_run(cfg):
    tasks, dataset_n = choose_tasks(cfg)
    pk = cfg["pass_at_k"]
    print(f"suite    {cfg['suite_name']}")
    print(f"reward   {cfg['task']['reward']}   dataset {cfg['task']['dataset']} "
          f"({dataset_n} tasks)")
    print(f"subset   {len(tasks)} prompts x {pk['samples_per_prompt']} samples, "
          f"ks={pk['ks']}, seed={cfg['seed']}")
    print(f"prompt   prompts/{task_template(cfg)}")
    print(f"output   {cfg['report']['output_dir']}/{cfg['suite_name']}/<slug>/")
    print("models:")
    for m in cfg["models"]:
        print(f"  {m['name']:<38} -> {resolve_model_id(m['name'])}"
              f"   thinking={m['enable_thinking']}"
              f" max_new_tokens={m['max_new_tokens']}"
              + ("" if m.get("chat", True) else " chat=False (raw)")
              + (f" adapter={m['adapter']}" if m.get("adapter") else ""))
    rendered = render_vp_task(tasks[0], template=task_template(cfg))
    print("\nsample prompt " + "-" * 60)
    if len(rendered) > 900:
        print(rendered[:260] + f"\n  [... {len(rendered)} chars total ...]\n"
              + rendered[-480:])
    else:
        print(rendered)


def self_test(cfg):
    """End-to-end run of scoring + reports with a deterministic stub generator
    (no GPU, no network). Patterns cycle per (task, sample):
      0 perfect  1 wrong-form  2 correct-but-no-thinking (reward 0.85, the
      pass_threshold edge)  3 gold form present but NO tags (also marked
      truncated) -- hits exact@k but not pass@k, proving the format-blind
      metric diverges from the tagged one."""
    tasks, _ = choose_tasks(cfg)
    n = cfg["pass_at_k"]["samples_per_prompt"]
    patterns = []  # patterns[ti][si] for expected-value bookkeeping

    def stub(model_cfg, prompts, pk, seed):
        records = []
        for ti in range(len(prompts)):
            row, recs = [], []
            for si in range(n):
                p = (ti + si) % 4
                gold = tasks[ti]["gold_devanagari"][0]
                text = {
                    0: f"<thinking>derivation</thinking>\n<answer>{gold}</answer>",
                    1: "<thinking>derivation</thinking>\n<answer>क्ष्क्ष्क्ष्</answer>",
                    2: f"<answer>{gold}</answer>",
                    3: f"the correct form is {gold} but there are no tags here",
                }[p]
                row.append(p)
                recs.append({"text": text, "tokens": len(text), "truncated": p == 3})
            patterns.append(row)
            records.append(recs)
        return records, {"load_s": 0.0, "gen_s": 1e-3,
                         "device": "cpu", "engine": "stub"}

    summary, out_dir = run_one(cfg, 0, generate_fn=stub,
                               subdir="self-test", lookup_params=False)

    flat = [p for row in patterns for p in row]
    kmax = str(max(cfg["pass_at_k"]["ks"]))
    exp_pass1 = float(np.mean([[p in (0, 2) for p in row].count(True) / n
                               for row in patterns]))
    exp_exact1 = float(np.mean([[p in (0, 2, 3) for p in row].count(True) / n
                                for row in patterns]))
    exp_tag = sum(p in (0, 1, 2) for p in flat) / len(flat)
    assert abs(summary["pass_at_k"]["1"] - exp_pass1) < 1e-9, "pass@1 mismatch"
    assert abs(summary["exact_at_k"]["1"] - exp_exact1) < 1e-9, "exact@1 mismatch"
    assert summary["pass_at_k"][kmax] == 1.0
    assert summary["exact_at_k"][kmax] == 1.0
    # pattern 3 hits exact@k but not pass@k: the two metrics MUST diverge here
    assert summary["exact_at_k"]["1"] > summary["pass_at_k"]["1"]
    assert abs(summary["answer_tag_rate"] - exp_tag) < 1e-9, "tag rate mismatch"
    assert abs(summary["truncated_frac"] - flat.count(3) / len(flat)) < 1e-9

    rows = json.loads((out_dir / "samples.json").read_text())
    assert len(rows) == len(tasks)
    for row, task in zip(rows, tasks):
        assert row["input_task"]["id"] == task["id"]
        assert row["prompt"] == render_vp_task(task, template=task_template(cfg))
        assert len(row["outputs"]) == n == len(row["output_devanagari"]) \
            == len(row["exact_answers"])
        # extractions must come from the stored raw outputs
        for raw, out, ok in zip(row["outputs"], row["output_devanagari"],
                                row["exact_answers"]):
            if out is not None:
                assert out in raw
            if ok:
                assert out in task["gold_devanagari"]
    print(f"self-test passed: {out_dir}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("config", nargs="?", default="prevals/outputs/configs/v1/eval-config.yml")
    ap.add_argument("--model-index", type=int, default=None,
                    help="(internal) run a single model in this process")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    config_path = Path(args.config).resolve()
    cfg = load_suite(config_path)
    if args.dry_run:
        dry_run(cfg)
    elif args.self_test:
        self_test(cfg)
    elif args.model_index is not None:
        run_one(cfg, args.model_index)
    else:
        sweep(cfg, config_path)


if __name__ == "__main__":
    main()
