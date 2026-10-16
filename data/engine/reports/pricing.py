#!/usr/bin/env python3
"""Build the offline calculator: python3 data/engine/reports/pricing.py.

No model calls. Rates were checked against the linked official model pages.
"""

import hashlib
from html import escape
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DATA = ROOT / "data/datasets"
OUTPUT = ROOT / "data/benchmark"
RUN = OUTPUT / "answer-only-pilot-20261013"
FAMILIES = {"tinanta": "Tiṅanta", "krdanta": "Kṛdanta", "subanta": "Subanta", "taddhitanta": "Taddhitānta"}
MODEL_SPECS = [
    ("gpt-6-astra", "GPT-6 Astra", "OpenAI", 10, 50),
    ("gpt-6-sol", "GPT-6 Sol", "OpenAI", 2, 10),
    ("gpt-6-luna", "GPT-6 Luna", "OpenAI", .1, .5),
    ("claude-opus-5-5", "Opus 5.5", "Anthropic", 4, 20),
    ("claude-sonnet-5-5", "Sonnet 5.5", "Anthropic", 2, 10),
    ("claude-haiku-5-5", "Haiku 5.5", "Anthropic", .1, .5),
]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    token_report = read(DATA / "token-costs.json")
    run, receipts = read(RUN / "run.json"), read(RUN / "results.json")
    samples = read(RUN / "samples.json")
    assert run["response_format"] == "answer_only" and run["comparison"]["identical_tasks_and_gold"]
    assert sha(RUN / "samples.json") == run["samples_sha256"]
    assert read(RUN / "verification.json")["passed"] and len(receipts) == 200
    calibration = {}
    sample_lookup = {(s["family"], s["sample"]): s for s in samples}
    for key, model_id in run["models"].items():
        calibration[model_id] = {}
        for family in FAMILIES:
            attempts = [r for r in receipts if r["model_key"] == key and r["family"] == family]
            assert len(attempts) == len({r["task_id"] for r in attempts}) == 25
            for row in attempts:
                sample = sample_lookup[family, row["sample"]]
                assert sample["task_id"] == row["task_id"] and sample["prompt_sha256"] == row["prompt_sha256"]
                assert "<thinking>" not in sample["prompt"]
                request = read(RUN / f"{key}-{family}-{row['sample']:02}.request.json")
                assert request["model"] == row["actual_model"] == model_id
                if key == "astra":
                    assert request["reasoning"]["effort"] == "xhigh" and "max_output_tokens" not in request
                    assert request["input"][0]["content"] == sample["prompt"]
                else:
                    assert request["output_config"]["effort"] == "xhigh" and request["max_tokens"] == 128000
                    assert request["thinking"]["type"] == "adaptive"
                    assert request["messages"][0]["content"] == sample["prompt"]
            answered = [r for r in attempts if r["status"] == "completed" and not r["structured_safety_flag"] and not r["structured_cyber_flag"]]
            assert answered and all(r["usage"] for r in answered), (model_id, family)
            # These short prompts are uncached; reject a changed assumption.
            assert all(not r["usage"].get("cache_read_input_tokens", 0) and not r["usage"].get("cache_creation_input_tokens", 0)
                       and not r["usage"].get("input_tokens_details", {}).get("cached_tokens", 0) for r in answered)
            calibration[model_id][family] = {
                "attempts": 25, "usable_responses": len(answered),
                "refusals": sum(r["structured_safety_flag"] for r in attempts),
                "cyber_flags": sum(r["structured_cyber_flag"] for r in attempts),
                "correct": sum(r["answer_correct"] for r in attempts),
                "input_tokens": statistics.mean(r["usage"]["input_tokens"] for r in answered),
                "output_tokens": statistics.mean(r["usage"]["output_tokens"] for r in answered),
                "max_output_tokens": max(r["usage"]["output_tokens"] for r in answered),
                "total_observed_cost_usd": sum(r["usage_based_cost_usd"] or 0 for r in attempts),
                "mean_cost_per_attempt_usd": statistics.mean(r["usage_based_cost_usd"] or 0 for r in attempts),
                "mean_cost_per_nonrefused_response_usd": statistics.mean(r["usage_based_cost_usd"] for r in answered),
                "task_ids": [r["task_id"] for r in answered],
                "excluded_from_usage_baseline": [r["task_id"] for r in attempts if r not in answered],
            }
    families = []
    for family, label in FAMILIES.items():
        manifest = read(DATA / family / "manifest.json")
        estimate = token_report["datasets"][family]
        assert manifest["generation_complete"]
        assert sha(DATA / family / "manifest.json") == run["sources"][family]["manifest_sha256"]
        assert estimate["source_sha256"] == manifest["files"]["full.json"]["sha256"]
        assert estimate["records"] == manifest["counts"]["full"]
        assert estimate["template_sha256"] == sha(ROOT / f"data/engine/prompts/v2/vp_{family}.txt")
        families.append({"id": family, "name": label, "available": manifest["counts"]["full"],
                         "prompt_tokens_proxy_10000": estimate["tokens"]["o200k_base"]["prompt_tokens"]["mean"],
                         "full_sha256": estimate["source_sha256"], "manifest_sha256": sha(DATA / family / "manifest.json"),
                         "template_sha256": estimate["template_sha256"]})
    models = []
    for model_id, name, provider, input_rate, output_rate in MODEL_SPECS:
        anchor = "gpt-6-astra" if provider == "OpenAI" else "claude-opus-5-5"
        measured = model_id == anchor
        source = (f"https://developers.openai.com/api/docs/models/{model_id}" if provider == "OpenAI"
                  else f"https://platform.claude.com/docs/en/models/{model_id.removeprefix('claude-')}/overview")
        models.append({"id": model_id, "name": name, "provider": provider, "input_rate": input_rate,
                       "output_rate": output_rate, "effort": "xhigh", "source": source,
                       "measured": measured, "calibration_model": anchor,
                       "output_basis": ("Measured on these answer-only prompts" if measured else f"Unmeasured; {anchor} token-usage proxy"),
                       "token_estimates": {f: {k: calibration[anchor][f][k] for k in ("input_tokens", "output_tokens")} for f in FAMILIES}})
    config = {
        "schema_version": 2, "pricing_checked_date": "2026-10-13", "currency": "USD", "models": models, "families": families,
        "budgets": {"OpenAI": 3000, "Anthropic": 1500}, "default_tasks_per_family": 1000,
        "input_basis": "Provider-reported input tokens, including API framing, from the answer-only pilot; each unmeasured model uses its provider's measured model as a proxy.",
        "output_basis": "Provider-reported output tokens for completed, nonrefused responses; hidden reasoning included once. Astra and Opus measured separately; other models are explicitly unmeasured proxies.",
        "calibration": {"run": str(RUN.relative_to(ROOT)), "response_format": "answer_only", "requests": 200, "by_model": calibration},
        "refusal_handling": "Refusals/errors remain in the observed per-attempt costs but are excluded from the successful-response usage baseline. The calculator does not assume future refusals will reduce spend.",
        "assumptions": "One response per task per selected model; standard global uncached short-input pricing by default; no tools, retries, taxes, regional premiums, or prior spend.",
        "sources": {str(p.relative_to(ROOT)): sha(p) for p in (DATA / "token-costs.json", RUN / "run.json", RUN / "results.json", RUN / "verification.json")},
    }
    model_rows = "".join(
        f'<tr><td><label><input type="checkbox" id="model-{m["id"]}" data-model="{m["id"]}" checked> '
        f'{escape(m["name"])} xHigh</label></td><td>{m["provider"]}</td><td>${m["input_rate"]:g}</td>'
        f'<td>${m["output_rate"]:g}</td><td><label>× <input id="scale-{m["id"]}" data-scale="{m["id"]}" '
        f'type="number" min="0.1" max="10" step="0.1" value="1" aria-label="{m["name"]} output token multiplier"></label></td>'
        f'<td>{escape(m["output_basis"])}</td><td><a href="{m["source"]}">Official pricing</a></td></tr>'
        for m in models)
    task_rows = "".join(
        f'<tr><th scope="row"><label for="count-{f["id"]}">{f["name"]}</label></th>'
        f'<td><input type="range" id="slider-{f["id"]}" data-slider="{f["id"]}" min="0" max="10000" step="1" value="1000" '
        f'aria-label="{f["name"]} task count"></td><td><input type="number" id="count-{f["id"]}" data-count="{f["id"]}" '
        f'min="0" max="{f["available"]}" step="1" value="1000"></td><td>{f["available"]:,}</td>'
        f'<td><output id="share-{f["id"]}"></output></td></tr>' for f in families)
    token_rows = "".join(
        f'<tr><th scope="row">{m["name"]}</th><td>{f["name"]}</td><td>{c["input_tokens"]:,.1f}</td><td>{c["output_tokens"]:,.1f}</td>'
        f'<td>{c["usable_responses"]} / {c["attempts"]}</td><td>{c["refusals"]}</td><td>{c["max_output_tokens"]:,}</td>'
        f'<td>${c["mean_cost_per_attempt_usd"]:.6f}</td><td>${c["mean_cost_per_nonrefused_response_usd"]:.6f}</td></tr>'
        for m in models if m["measured"] for f in families for c in [calibration[m["id"]][f["id"]]])
    html = (HERE / "pricing.template.html").read_text()
    replacements = {"MODELS": model_rows, "TASKS": task_rows, "TOKENS": token_rows,
                    "CONFIG": json.dumps(config, ensure_ascii=False).replace("<", "\\u003c"),
                    "SCRIPT": (HERE / "pricing.js").read_text()}
    for key, value in replacements.items():
        html = html.replace("@@" + key + "@@", value)
    assert "@@" not in html
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "pricing-data.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
    (OUTPUT / "pricing.html").write_text(html)
    print(f"Wrote {OUTPUT / 'pricing.html'}; six models, four families, 200 answer-only pilot requests.")


if __name__ == "__main__":
    build()
