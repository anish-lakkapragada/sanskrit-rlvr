"""Estimate current prompt lengths and API costs without generating completions.

Run from the repository root:
    uv run --python 3.11 --with tiktoken==0.14.0 --with vidyut==0.4.0 \
        python data/engine/reports/token_costs.py

Neither named provider model has a tiktoken mapping. Both encodings below are
explicitly proxies, not provider-exact counts. Output lengths are scenarios;
historical usage is recorded separately and is not a forecast for new tasks.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import random
import statistics
import subprocess
import sys

import tiktoken

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.krdanta import common as krdanta
from data.engine.subanta import common as subanta
from data.engine.taddhitanta import common as taddhitanta
from data.engine.tinanta import common as tinanta

SAMPLE_SIZE = 10_000
SEED = "sanskrit-token-costs-2026-10-12"
ENCODINGS = {name: tiktoken.get_encoding(name) for name in ("o200k_base", "cl100k_base")}
RENDERERS = {"tinanta": tinanta.render_task, "krdanta": krdanta.render_task,
             "subanta": subanta.render_task, "taddhitanta": taddhitanta.render_task}


def stats(values):
    values = sorted(values)
    return {"n": len(values), "mean": round(statistics.mean(values), 3),
            "min": values[0], "median": statistics.median(values),
            "p95": values[math.ceil(len(values) * .95) - 1], "max": values[-1]}


def sampled_rows(path, total, indices):
    """Verify the complete source; only parse selected records to keep memory low."""
    digest = hashlib.sha256()
    rows, count = [], 0
    with path.open("rb") as f:
        opening = next(f)
        assert opening == b"[\n", path
        digest.update(opening)
        for line in f:
            digest.update(line)
            stripped = line.strip()
            if stripped == b"]":
                assert not f.read(), "Trailing content"
                break
            assert stripped.startswith(b"{") and stripped.endswith((b"},", b"}")), path
            if count in indices:
                rows.append(json.loads(stripped.removesuffix(b",")))
            count += 1
        else:
            raise ValueError(f"Unterminated dataset: {path}")
    assert count == total and len(rows) == len(indices), (path, count, total)
    return rows, digest.hexdigest()


def historical_usage():
    revision = subprocess.check_output(
        ["git", "rev-parse", "finetune/vidyut-prakriya"], cwd=ROOT, text=True).strip()

    def read(path):
        return json.loads(subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT))

    path = "benchmarks/analysis/performance-study/study.json"
    study = read(path)
    runs = []
    for row in study["models"]:
        if row["id"] not in {"claude-opus-5-5-xhigh", "gpt-6-astra-xhigh"}:
            continue
        runs.append({"model_effort": row["id"], "task_family": "tinanta",
                     "requests": 6687, "output_tokens": row["output_tokens"],
                     "mean_output_tokens": row["output_per_task"],
                     "source": path, "original_source": row["source"],
                     "caveat": ("Older task mix and template. " +
                                ("Astra's v1 prompt already requested a visible thinking block."
                                 if row["id"].startswith("gpt-") else
                                 "Opus's v2 prompt requested only the answer, without a visible thinking block."))})
    path = "benchmarks/iterative-goal-20261006/jobs/opus-krdanta-01/summary.json"
    run = read(path)
    runs.append({"model_effort": "claude-opus-5-5-xhigh", "task_family": "krdanta",
                 "requests": run["n"], "usage": run["usage"],
                 "mean_output_tokens": run["usage"]["output_tokens"] / run["n"],
                 "source": path,
                 "caveat": "Different, more complex task: derived roots plus inflection; answer-only prompt; seven refusals included."})
    return {"git_revision": revision, "runs": runs,
            "unmeasured_current_task_families": ["subanta", "taddhitanta"]}


def main():
    sample_root = ROOT / "data/engine/prompts/v2/samples"
    samples = json.loads((sample_root / "manifest.json").read_text())
    for family, render in RENDERERS.items():
        for sample in samples["datasets"][family]["samples"]:
            assert render(sample["inputs"]) == (sample_root / sample["path"]).read_text(), sample["path"]

    report = {
        "pricing_checked_date": "2026-10-12", "currency": "USD",
        "method": "Uniform sample of 10,000 distinct records per current full.json; whole-file SHA256 and row count verified; all 20 saved prompts match hydration.",
        "tokenizer": {"package": f"tiktoken=={importlib.metadata.version('tiktoken')}",
                      "primary_proxy": "o200k_base", "sensitivity_proxy": "cl100k_base",
                      "caveat": "Neither encoding is verified as the tokenizer of Astra or Opus 5.5. Prompt text only; API framing/system/tool overhead excluded. The two proxies do not establish bounds on actual provider counts."},
        "rates_per_million_tokens": {
            "claude-opus-5-5": {"input": 4, "output": 20, "source": "https://platform.claude.com/docs/en/about-claude/pricing"},
            "gpt-6-astra": {"input": 10, "output": 50, "source": "https://developers.openai.com/api/docs/models/gpt-6-astra"},
        },
        "cost_assumptions": "Standard, uncached, global API requests, no tools or retries. Current prompts request only an <answer> block. Total billed output still includes native reasoning and visible response text. Batch is half the standard cost; Fast is double.",
        "output_scenarios": [1000, 2000, 4000, 8000, 16384],
        "output_scenarios_are_predictions": False,
        "historical_usage": historical_usage(), "datasets": {},
    }
    for family, render in RENDERERS.items():
        folder = ROOT / "data/datasets" / family
        metadata = json.loads((folder / "manifest.json").read_text())
        total = metadata["counts"].get("full", metadata["counts"].get("all"))
        seed = f"{SEED}:{family}"
        indices = set(random.Random(seed).sample(range(total), min(SAMPLE_SIZE, total)))
        rows, digest = sampled_rows(folder / "full.json", total, indices)
        recorded_hash = metadata["files"]["full.json"]["sha256"]
        assert digest == recorded_hash, family
        prompts = [render(row) for row in rows]
        forms = [row["gold_devanagari"] for row in rows]
        assert all(forms), "Non-answerable sample"
        measures = {}
        for name, encoding in ENCODINGS.items():
            lengths = [len(tokens) for tokens in encoding.encode_ordinary_batch(prompts)]
            # A valid model answer is ONE accepted form, not the gold JSON array.
            answers = [statistics.mean(len(encoding.encode_ordinary(f"<answer>{form}</answer>"))
                                       for form in variants) for variants in forms]
            measures[name] = {"prompt_tokens": stats(lengths),
                              "answer_block_tokens_mean_over_accepted_forms_per_task": stats(answers)}
        mean_input = measures["o200k_base"]["prompt_tokens"]["mean"]
        costs = {model: {str(out): round((mean_input * rate["input"] + out * rate["output"]) / 1e6, 8)
                         for out in report["output_scenarios"]}
                 for model, rate in report["rates_per_million_tokens"].items()}
        template = ROOT / f"data/engine/prompts/v2/vp_{family}.txt"
        report["datasets"][family] = {
            "source": str((folder / "full.json").relative_to(ROOT)), "source_sha256": digest,
            "records": total, "sampling_seed": seed, "sample_size": len(rows),
            "template_sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
            "prompt_characters": stats([len(p) for p in prompts]), "tokens": measures,
            "standard_usd_per_request_by_total_output_tokens": costs,
        }
        print(f"{family}: {mean_input:.1f} mean prompt tokens (proxy); {len(rows):,} samples", flush=True)
    output = ROOT / "data/datasets/token-costs.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"Saved {output}", flush=True)


if __name__ == "__main__":
    main()
