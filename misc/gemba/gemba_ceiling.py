#!/usr/bin/env python
"""GEMBA sensitivity/calibration to verb morphology (judge: claude-opus-5).

The GEMBA analog of misc/answer-key-ceiling: feed the judge three versions of
each covered Samayik reference as the "machine translation" —
  orig   : the reference itself (upper anchor / judge false-positive floor)
  flip   : ONLY the finite verbs' number flipped (real paradigm siblings,
           vetted pairs from misc/answer-key-ceiling/verb_ceiling_v0.py)
  delete : the verbs removed outright (worst case)
and score each with GEMBA-DA_ref (reference = the true original) and GEMBA-MQM
(reference-free). Because the injected error token is KNOWN, MQM output spans
give the judge's detection rate on ground-truth wrong inflections.

Usage: uv run python misc/gemba/gemba_ceiling.py [--smoke] [--workers 8]
Writes results/ceiling-<metric>-<arm>.jsonl (chunk-idempotent) + prints the
analysis; --analyze-only re-runs analysis from files.
"""

import argparse
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "answer-key-ceiling"))
from gemba_eval import (JUDGE, MAX_TOKENS, MQM_SYSTEM, da_messages,  # noqa: E402
                        mqm_messages, parse_da, parse_mqm)
from verb_ceiling_v0 import EVAL, corrupt_sentence, is_hindi  # noqa: E402

RESULTS = HERE / "results"
ARMS = ("orig", "flip", "delete")


def build_rows():
    """Covered refs only: [(idx, en, ref, {arm: text}, [(orig_tok, flip_tok)])]."""
    rows = []
    for i, r in enumerate(json.loads(EVAL.read_text())):
        sa = " ".join(r["sa"].split())
        if is_hindi(sa):
            continue
        flip, n, pairs = corrupt_sentence(sa, "flip")
        if n == 0:
            continue
        delete, _, _ = corrupt_sentence(sa, "delete")
        rows.append((i, " ".join(r["en"].split()), sa,
                     {"orig": sa, "flip": flip, "delete": delete}, pairs))
    return rows


def run_chunk(client, rows, metric, arm, workers):
    out_path = RESULTS / f"ceiling-{metric}-{arm}.jsonl"
    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"skip {out_path.name} (exists)")
        return
    def call(row):
        idx, en, ref, hyps, _ = row
        hyp = hyps[arm]
        if metric == "mqm":
            msgs, kw = mqm_messages(en, hyp), {"system": MQM_SYSTEM}
        else:
            msgs, kw = da_messages(en, ref, hyp), {}
        r = client.messages.create(model=JUDGE, max_tokens=MAX_TOKENS[metric],
                                   thinking={"type": "disabled"}, messages=msgs, **kw)
        text = next((b.text for b in r.content if b.type == "text"), "")
        return {"idx": idx, "arm": arm, "metric": metric, "text": text,
                "in": r.usage.input_tokens, "out": r.usage.output_tokens}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(call, rows))
    with open(out_path, "w") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {out_path.name} ({len(results)} calls)")


def boot_ci(vals, iters=2000, seed=0):
    rng = random.Random(seed)
    n = len(vals)
    ms = sorted(sum(rng.choices(vals, k=n)) / n for _ in range(iters))
    return sum(vals) / n, ms[int(0.025 * iters)], ms[int(0.975 * iters)]


def analyze(rows):
    pairs_by_idx = {r[0]: r[4] for r in rows}
    data = {}   # (metric, arm) -> {idx: parsed}
    tok_in = tok_out = 0
    for metric in ("da", "mqm"):
        for arm in ARMS:
            path = RESULTS / f"ceiling-{metric}-{arm}.jsonl"
            d = {}
            for line in path.read_text().splitlines():
                r = json.loads(line)
                tok_in += r["in"]; tok_out += r["out"]
                d[r["idx"]] = r["text"]
            data[(metric, arm)] = d

    print(f"\n=== GEMBA verb-morphology sensitivity (judge {JUDGE}, n={len(rows)} refs, "
          f"{sum(len(p) for p in pairs_by_idx.values())} corrupted verbs) ===")

    # ---- DA_ref: absolute per arm + paired deltas vs orig
    da = {arm: {i: parse_da(t) for i, t in data[("da", arm)].items()} for arm in ARMS}
    common = [i for i in da["orig"] if all(da[a].get(i) is not None for a in ARMS)]
    print(f"\nGEMBA-DA_ref (paired on {len(common)} refs):")
    for arm in ARMS:
        m, lo, hi = boot_ci([da[arm][i] for i in common])
        print(f"  {arm:6}: mean {m:6.2f} [{lo:.2f}, {hi:.2f}]")
    for arm in ("flip", "delete"):
        m, lo, hi = boot_ci([da[arm][i] - da["orig"][i] for i in common])
        print(f"  Δ {arm:6} vs orig: {m:+.2f} [{lo:+.2f}, {hi:+.2f}]")

    # ---- MQM: score + grammar counts per arm; detection on flip
    print(f"\nGEMBA-MQM:")
    mqm = {}
    for arm in ARMS:
        parsed = {i: parse_mqm(t) for i, t in data[("mqm", arm)].items()}
        mqm[arm] = parsed
        scores = [s for s, _ in parsed.values()]
        m, lo, hi = boot_ci(scores)
        n = len(parsed)
        def rate(prefix):
            return 100 * sum(c.startswith(prefix) for _, cl in parsed.values()
                             for lv in cl.values() for c in lv) / n
        print(f"  {arm:6}: mean {m:+6.2f} [{lo:+.2f}, {hi:+.2f}]  "
              f"gram/100 {rate('fluency-grammar'):5.1f}  "
              f"omission/100 {rate('accuracy-omission'):5.1f}  "
              f"mistrans/100 {rate('accuracy-mistranslation'):5.1f}  "
              f"nontrans/100 {rate('non-translation'):5.1f}")
    ci = [i for i in mqm["orig"] if i in mqm["flip"]]
    m, lo, hi = boot_ci([mqm["flip"][i][0] - mqm["orig"][i][0] for i in ci])
    print(f"  Δ flip   vs orig: {m:+.2f} [{lo:+.2f}, {hi:+.2f}]")
    m, lo, hi = boot_ci([mqm["delete"][i][0] - mqm["orig"][i][0]
                         for i in mqm["orig"] if i in mqm["delete"]])
    print(f"  Δ delete vs orig: {m:+.2f} [{lo:+.2f}, {hi:+.2f}]")

    # ---- detection: does any MQM error line on the flip arm quote the flipped token?
    det_verb = det_ref = 0
    n_verbs = 0
    fp_lines = 0
    for i, text in data[("mqm", "flip")].items():
        for orig_tok, flip_tok in pairs_by_idx[i]:
            n_verbs += 1
            if flip_tok and flip_tok in text:
                det_verb += 1
        if any(err for _, cl in [mqm["flip"][i]] for lv in cl.values() for err in lv):
            det_ref += 1
    for i, text in data[("mqm", "orig")].items():
        s, cl = mqm["orig"][i]
        fp_lines += sum(c.startswith("fluency-grammar") for lv in cl.values() for c in lv)
    print(f"\nDetection on injected wrong inflections (span quotes flipped token): "
          f"{det_verb}/{n_verbs} = {100 * det_verb / n_verbs:.1f}%")
    print(f"Gold-reference false-positive floor: {fp_lines} fluency-grammar flags "
          f"on {len(mqm['orig'])} gold refs = {100 * fp_lines / len(mqm['orig']):.1f}/100 "
          f"(includes real corpus noise, e.g. OCR typos)")

    cost = tok_in / 1e6 * 5 + tok_out / 1e6 * 25
    print(f"\ntokens in={tok_in:,} out={tok_out:,}  standard-API cost ≈ ${cost:.2f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smoke", action="store_true", help="5 refs only")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--analyze-only", action="store_true")
    args = ap.parse_args()

    RESULTS.mkdir(exist_ok=True)
    rows = build_rows()
    print(f"covered refs: {len(rows)}")
    if args.smoke:
        rows = rows[:5]
        for metric in ("da", "mqm"):
            for arm in ARMS:
                p = RESULTS / f"ceiling-{metric}-{arm}.jsonl"
                if p.exists():
                    p.unlink()
    if not args.analyze_only:
        client = anthropic.Anthropic(max_retries=8)
        for metric in ("da", "mqm"):
            for arm in ARMS:
                run_chunk(client, rows, metric, arm, args.workers)
    analyze(rows)


if __name__ == "__main__":
    main()
