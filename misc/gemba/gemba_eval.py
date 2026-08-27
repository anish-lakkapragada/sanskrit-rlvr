#!/usr/bin/env python
"""GEMBA-DA_ref + GEMBA-MQM (judge: claude-opus-5) over the campaign's saved
translation outputs — Samayik (750) + FLORES-200 (2,009) for the 17 table
models. No GPU: hypotheses already live in runs-final/*/evals-final/.

Templates are VERBATIM from MicrosoftTranslator/GEMBA (_upstream_prompt.py,
_upstream_mqm.py, vendored next to this file):
  - GEMBA-DA_ref : scalar 0-100, reference-based, single user turn.
  - GEMBA-MQM    : reference-free QE, fixed 3-shot (en-de, en-cs, zh-en)
                   error-span annotation; score = -(25*crit + 5*major + 1*minor),
                   first 5 errors only, floored at -25 (upstream parser port).

Protocol: tag-conditional — exactly the samples with non-empty `hyp`, i.e. the
same denominators as the chrF columns in misc/figures/data-mixture-results.md.
Single judge, temperature 0.

Subcommands:
  smoke      run a few segments per model synchronously, print outputs + cost projection
  submit     build + submit Batch API shards (records ids in results/batches.json)
  status     print processing status of all recorded batches
  fetch      download results of ended batches -> results/raw-<shard>.jsonl
  summarize  aggregate -> markdown tables + results/summary.json

Usage: uv run python misc/gemba/gemba_eval.py <subcommand>
"""

import argparse
import json
import random
import re
import time
from collections import defaultdict
from pathlib import Path

import anthropic

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
RESULTS = HERE / "results"

JUDGE = "claude-opus-5"
MAX_TOKENS = {"mqm": 384, "da": 256}  # da usually 1-3 tok; headroom for CoT preambles
SHARD_MAX = 15_000  # requests per batch shard (limit 100k/256MB; stay small)

# model key (short, custom_id-safe) -> (table label, evals-final dir)
def _arm(budget, share):
    return (f"{budget}M · {share}% samayik",
            f"runs-final/sft-qwen3-4b-tb{budget}m-samayik{share}/evals-final")

MODELS = {"base": ("Qwen3-4B (base)", "runs-final/base-qwen3-4b/evals-final")}
for _b in (10, 15, 20):
    for _s in (100, 67, 50, 33, 0):
        MODELS[f"t{_b}s{_s}"] = _arm(_b, _s)
MODELS["grpo"] = ("GRPO-r3 final (step 731)",
                  "runs-final/grpo-r3-finals-results/finals/final731-translation")

DATASETS = {"smk": ("Samayik", "final-samayik.json"),
            "flo": ("FLORES-200", "final-flores-200.json")}

# ---------------------------------------------------------------- prompts ---

DA_REF_TEMPLATE = (
    'Score the following translation from {source_lang} to {target_lang} with '
    'respect to human reference on a continuous scale 0 to 100 where score of '
    'zero means "no meaning preserved" and score of one hundred means "perfect '
    'meaning and grammar".\n\n'
    '{source_lang} source: "{source_seg}"\n'
    '{target_lang} human reference: {reference_seg}\n'
    '{target_lang} machine translation: "{target_seg}"\n'
    'Score: '
)

MQM_SYSTEM = ("You are an annotator for the quality of machine translation. "
              "Your task is to identify errors and assess the quality of the translation.")

MQM_TEMPLATE = """{source_lang} source:
```{source_seg}```
{target_lang} translation:
```{target_seg}```

Based on the source segment and machine translation surrounded with triple backticks, identify error types in the translation and classify them. The categories of errors are: accuracy (addition, mistranslation, omission, untranslated text), fluency (character encoding, grammar, inconsistency, punctuation, register, spelling), style (awkward), terminology (inappropriate for context, inconsistent use), non-translation, other, or no-error.\nEach error is classified as one of three categories: critical, major, and minor. Critical errors inhibit comprehension of the text. Major errors disrupt the flow, but what the text is trying to say is still understandable. Minor errors are technically errors, but do not disrupt the flow or hinder comprehension."""

MQM_FEW_SHOTS = [
    (dict(source_lang="English",
          source_seg="I do apologise about this, we must gain permission from the account holder to discuss an order with another person, I apologise if this was done previously, however, I would not be able to discuss this with yourself without the account holders permission.",
          target_lang="German",
          target_seg="Ich entschuldige mich dafür, wir müssen die Erlaubnis einholen, um eine Bestellung mit einer anderen Person zu besprechen. Ich entschuldige mich, falls dies zuvor geschehen wäre, aber ohne die Erlaubnis des Kontoinhabers wäre ich nicht in der Lage, dies mit dir involvement."),
     'Critical:\nno-error\nMajor:\naccuracy/mistranslation - "involvement"\naccuracy/omission - "the account holder"\nMinor:\nfluency/grammar - "wäre"\nfluency/register - "dir"\n'),
    (dict(source_lang="English",
          source_seg="Talks have resumed in Vienna to try to revive the nuclear pact, with both sides trying to gauge the prospects of success after the latest exchanges in the stop-start negotiations.",
          target_lang="Czech",
          target_seg="Ve Vídni se ve Vídni obnovily rozhovory o oživení jaderného paktu, přičemž obě partaje se snaží posoudit vyhlídky na úspěch po posledních výměnách v jednáních."),
     'Critical:\nno-error\nMajor:\naccuracy/addition - "ve Vídni"\naccuracy/omission - "the stop-start"\nMinor:\nterminology/inappropriate for context - "partaje"\n'),
    (dict(source_lang="Chinese",
          source_seg="大众点评乌鲁木齐家居卖场频道为您提供高铁居然之家地址，电话，营业时间等最新商户信息，找装修公司，就上大众点评",
          target_lang="English",
          target_seg="Urumqi Home Furnishing Store Channel provides you with the latest business information such as the address, telephone number, business hours, etc., of high-speed rail, and find a decoration company, and go to the reviews."),
     'Critical:\naccuracy/addition - "of high-speed rail"\nMajor:\naccuracy/mistranslation - "go to the reviews"\nMinor:\nstyle/awkward - "etc.,"\n'),
]


def mqm_messages(source_seg, target_seg):
    msgs = []
    for shot, answer in MQM_FEW_SHOTS:
        msgs.append({"role": "user", "content": MQM_TEMPLATE.format(**shot)})
        msgs.append({"role": "assistant", "content": answer})
    msgs.append({"role": "user", "content": MQM_TEMPLATE.format(
        source_lang="English", source_seg=source_seg,
        target_lang="Sanskrit", target_seg=target_seg)})
    return msgs


def da_messages(source_seg, reference_seg, target_seg):
    return [{"role": "user", "content": DA_REF_TEMPLATE.format(
        source_lang="English", target_lang="Sanskrit", source_seg=source_seg,
        reference_seg=reference_seg, target_seg=target_seg)}]


# ---------------------------------------------------------------- parsing ---

ERROR_CLASSES = ['accuracy', 'fluency', 'locale convention', 'style',
                 'terminology', 'non-translation', 'other']
SUBCLASSES = {
    "accuracy": ["addition", "mistranslation", "omission", "untranslated text"],
    "fluency": ["character encoding", "grammar", "inconsistency", "punctuation",
                "register", "spelling"],
    "locale convention": ["currency", "date", "name", "telephone", "time"],
    "terminology": ["inappropriate", "inconsistent"],
}


def parse_error_class(error: str) -> str:
    for cls in ERROR_CLASSES:
        if cls in error:
            for sub in SUBCLASSES.get(cls, []):
                if sub in error:
                    return f"{cls}-{sub}"
            return cls
    return "unknown"


def parse_mqm(text: str):
    """Upstream parse_mqm_answer port: (score in [-25, 0], {severity: [class]})."""
    errors = {"critical": [], "major": [], "minor": []}
    level = None
    for line in str(text).lower().split("\n"):
        line = line.strip()
        if "no-error" in line or "no error" in line or line == "":
            continue
        if line == "critical:":
            level = "critical"; continue
        if line == "major:":
            level = "major"; continue
        if line == "minor:":
            level = "minor"; continue
        if level is None:
            continue
        if "non-translation" in line:
            errors["critical"].append(line)
        else:
            errors[level].append(line)

    score, counted = 0, 0
    classes = defaultdict(list)
    for level in ("critical", "major", "minor"):
        for err in errors[level]:
            if counted < 5:
                score += 25 if level == "critical" else 5 if level == "major" else 1
                counted += 1
            classes[level].append(parse_error_class(err))
    return -min(score, 25), dict(classes)


def parse_da(text: str):
    s = re.sub(r"<thinking>.*?</thinking>", " ", str(text), flags=re.S)
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:  # unclosed CoT preamble etc. — fall back to the last number anywhere
        nums = re.findall(r"\d+(?:\.\d+)?", str(text))
        if not nums:
            return None
        val = float(nums[-1])
    else:
        val = float(m.group())
    return val if 0 <= val <= 100 else None


# ------------------------------------------------------------------- data ---

def load_segments(model_key: str, ds_key: str):
    """Segments with non-empty hyp (tag-conditional, matches table n)."""
    _, d = MODELS[model_key]
    path = ROOT / d / DATASETS[ds_key][1]
    samples = json.loads(path.read_text())["samples"]
    return [(i, s["en"], s["ref"], s["hyp"]) for i, s in enumerate(samples) if s["hyp"]]


def build_requests(metric: str, ds_key: str):
    reqs = []
    for mk in MODELS:
        for idx, en, ref, hyp in load_segments(mk, ds_key):
            if metric == "mqm":
                msgs, system = mqm_messages(en, hyp), MQM_SYSTEM
            else:
                msgs, system = da_messages(en, ref, hyp), None
            params = {"model": JUDGE, "max_tokens": MAX_TOKENS[metric],
                      "thinking": {"type": "disabled"}, "messages": msgs}
            if system:
                params["system"] = system
            reqs.append({"custom_id": f"{metric}-{ds_key}-{mk}-{idx:04d}",
                         "params": params})
    return reqs


# ------------------------------------------------------------- subcommands --

def cmd_smoke(args):
    client = anthropic.Anthropic()
    keys = ["base", "t20s67", "t20s0", "grpo"]
    usage_in = usage_out = calls = 0
    for mk in keys:
        segs = random.Random(7).sample(load_segments(mk, "smk"), args.n)
        for metric in ("mqm", "da"):
            for idx, en, ref, hyp in segs:
                msgs = mqm_messages(en, hyp) if metric == "mqm" else da_messages(en, ref, hyp)
                kw = {"system": MQM_SYSTEM} if metric == "mqm" else {}
                r = client.messages.create(model=JUDGE, max_tokens=MAX_TOKENS[metric],
                                           thinking={"type": "disabled"},
                                           messages=msgs, **kw)
                text = next((b.text for b in r.content if b.type == "text"), "")
                usage_in += r.usage.input_tokens; usage_out += r.usage.output_tokens
                calls += 1
                if metric == "mqm":
                    score, classes = parse_mqm(text)
                    print(f"[{mk} #{idx} MQM {score:+d}] {dict(classes)}")
                    if args.verbose:
                        print(f"    hyp: {hyp[:90]}")
                        print("    " + text.replace("\n", "\n    ")[:400])
                else:
                    print(f"[{mk} #{idx} DA {parse_da(text)}] raw={text!r:.60}")
    # project full-sweep cost from measured usage (batch rates: $2.5/$12.5 per MTok)
    n_total = {(m, d): sum(len(load_segments(mk, d)) for mk in MODELS)
               for m in ("mqm", "da") for d in ("smk", "flo")}
    per_in, per_out = usage_in / calls, usage_out / calls
    print(f"\nsmoke: {calls} calls, mean in={per_in:.0f} out={per_out:.0f} tokens")
    # flores segs are ~1.4x longer; crude split by metric only is fine for a guardrail
    total_calls = sum(n_total.values())
    est_in = per_in * total_calls * 1.15   # flores length bump
    est_out = per_out * total_calls
    cost = est_in / 1e6 * 2.5 + est_out / 1e6 * 12.5
    print(f"full sweep: {total_calls} calls, projected batch cost ≈ ${cost:.0f} "
          f"(guardrail: pause if > $350)")


def cmd_submit(args):
    client = anthropic.Anthropic()
    RESULTS.mkdir(exist_ok=True)
    book = {}
    for metric in ("mqm", "da"):
        for ds in ("smk", "flo"):
            reqs = build_requests(metric, ds)
            shards = [reqs[i:i + SHARD_MAX] for i in range(0, len(reqs), SHARD_MAX)]
            for si, shard in enumerate(shards):
                name = f"{metric}-{ds}-{si}"
                b = client.messages.batches.create(requests=shard)
                book[name] = {"id": b.id, "n": len(shard), "status": b.processing_status}
                print(f"submitted {name}: {b.id} ({len(shard)} requests)")
    (RESULTS / "batches.json").write_text(json.dumps(book, indent=2))
    print(f"total requests: {sum(v['n'] for v in book.values())}")


def cmd_status(args):
    client = anthropic.Anthropic()
    book = json.loads((RESULTS / "batches.json").read_text())
    done = 0
    for name, meta in book.items():
        b = client.messages.batches.retrieve(meta["id"])
        c = b.request_counts
        print(f"{name}: {b.processing_status}  ok={c.succeeded} err={c.errored} "
              f"proc={c.processing} exp={c.expired}/{meta['n']}")
        done += b.processing_status == "ended"
    print(f"ENDED {done}/{len(book)}")
    return done == len(book)


def cmd_fetch(args):
    client = anthropic.Anthropic()
    book = json.loads((RESULTS / "batches.json").read_text())
    for name, meta in book.items():
        out = RESULTS / f"raw-{name}.jsonl"
        if out.exists() and out.stat().st_size > 0:
            continue
        b = client.messages.batches.retrieve(meta["id"])
        if b.processing_status != "ended":
            print(f"{name}: still {b.processing_status}, skipping")
            continue
        n_ok = n_err = 0
        with open(out, "w") as f:
            for res in client.messages.batches.results(meta["id"]):
                row = {"custom_id": res.custom_id, "type": res.result.type}
                if res.result.type == "succeeded":
                    msg = res.result.message
                    row["text"] = next((b.text for b in msg.content if b.type == "text"), "")
                    row["in"], row["out"] = msg.usage.input_tokens, msg.usage.output_tokens
                    n_ok += 1
                else:
                    n_err += 1
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"{name}: fetched ok={n_ok} err={n_err} -> {out.name}")


def bootstrap_ci(vals, iters=1000, seed=0):
    rng = random.Random(seed)
    n = len(vals)
    means = sorted(sum(rng.choices(vals, k=n)) / n for _ in range(iters))
    return means[int(0.025 * iters)], means[int(0.975 * iters)]


def cmd_summarize(args):
    rows = defaultdict(dict)   # (model, ds) -> metric aggregates
    per_model = defaultdict(list)  # (metric, ds, model) -> list of scores
    cats = defaultdict(lambda: defaultdict(int))        # (ds, model) -> class counts
    tok_in = tok_out = fails = 0
    by_id = {}
    for raw in sorted(RESULTS.glob("raw-*.jsonl")):  # zz-patch files sort last, win
        for line in raw.read_text().splitlines():
            r = json.loads(line)
            by_id[r["custom_id"]] = r
    for r in by_id.values():
            metric, ds, mk, idx = r["custom_id"].split("-")
            if r["type"] != "succeeded":
                fails += 1
                continue
            tok_in += r.get("in", 0); tok_out += r.get("out", 0)
            if metric == "mqm":
                score, classes = parse_mqm(r["text"])
                per_model[("mqm", ds, mk)].append(score)
                for level, cls_list in classes.items():
                    for c in cls_list:
                        cats[(ds, mk)][c] += 1
                        cats[(ds, mk)][f"sev-{level}"] += 1
            else:
                v = parse_da(r["text"])
                if v is None:
                    fails += 1
                else:
                    per_model[("da", ds, mk)].append(v)

    summary = {}
    for (metric, ds, mk), vals in per_model.items():
        mean = sum(vals) / len(vals)
        lo, hi = bootstrap_ci(vals)
        summary[f"{metric}|{ds}|{mk}"] = {"mean": mean, "ci": [lo, hi], "n": len(vals)}

    lines = []
    for ds in ("smk", "flo"):
        lines.append(f"\n### {DATASETS[ds][0]} — GEMBA (judge: {JUDGE}, thinking disabled)\n")
        lines.append("| Model | GEMBA-DA_ref mean [95% CI] | GEMBA-MQM mean [95% CI] | "
                     "fluency-grammar /100 | acc-mistranslation /100 | non-translation /100 | n |")
        lines.append("|---|---|---|---|---|---|---|")
        for mk, (label, _) in MODELS.items():
            da = summary.get(f"da|{ds}|{mk}")
            mqm = summary.get(f"mqm|{ds}|{mk}")
            if not da or not mqm:
                continue
            n = mqm["n"]
            c = cats[(ds, mk)]
            gram = 100 * sum(v for k, v in c.items() if k.startswith("fluency-grammar")) / n
            mist = 100 * sum(v for k, v in c.items() if k.startswith("accuracy-mistranslation")) / n
            nont = 100 * c.get("non-translation", 0) / n
            lines.append(
                f"| {label} | {da['mean']:.1f} [{da['ci'][0]:.1f}, {da['ci'][1]:.1f}] "
                f"| {mqm['mean']:.2f} [{mqm['ci'][0]:.2f}, {mqm['ci'][1]:.2f}] "
                f"| {gram:.1f} | {mist:.1f} | {nont:.1f} | {n} |")
    table = "\n".join(lines)
    print(table)
    cost = tok_in / 1e6 * 2.5 + tok_out / 1e6 * 12.5
    print(f"\ntokens: in={tok_in:,} out={tok_out:,}  batch cost ≈ ${cost:.2f}  "
          f"failed/unparsed: {fails}")
    (RESULTS / "summary.json").write_text(json.dumps(
        {"summary": summary,
         "categories": {f"{ds}|{mk}": dict(v) for (ds, mk), v in cats.items()},
         "tokens_in": tok_in, "tokens_out": tok_out, "est_cost_usd": cost,
         "judge": JUDGE, "failed": fails}, indent=2))
    (RESULTS / "tables.md").write_text(table + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sm = sub.add_parser("smoke"); sm.add_argument("-n", type=int, default=4)
    sm.add_argument("--verbose", action="store_true")
    sub.add_parser("submit"); sub.add_parser("status")
    sub.add_parser("fetch"); sub.add_parser("summarize")
    args = ap.parse_args()
    {"smoke": cmd_smoke, "submit": cmd_submit, "status": cmd_status,
     "fetch": cmd_fetch, "summarize": cmd_summarize}[args.cmd](args)


if __name__ == "__main__":
    main()
