#!/usr/bin/env python
"""Answer-key ceiling, v0 (metric-side): how much is verb morphology worth to chrF?

Take the 750 Samayik eval references, corrupt ONLY finite-verb inflection
(number flip: singular <-> plural, the MorphEval-style minimal contrast), and
score corrupted-reference against the true reference. The result is the chrF
of a translation that is perfect in every way except every (identified) verb
is inflected wrong -- an upper bound on what verb-morphology skill can ever be
worth on this benchmark.

v0 identifies verbs by high-precision tinanta ending patterns instead of a
morphological analyzer. Precision guards:
  - string swaps are applied only where they provably yield the real Sanskrit
    form: thematic stems (plain consonant with inherent -a- before the ending),
    e.g. gacchati -> gacchanti; athematic stems go through an explicit
    irregular map (asti <-> santi, karoti <-> kurvanti, ...) or are skipped;
  - short/ambiguous endings (-ti, -te, -tu) additionally require clause-final
    position (last token before a danda or end of string);
  - particle/noun blocklist (iti, vastu, hetu, ...);
  - rows that look like Hindi (the eval set contains some) are excluded.

Usage: uv run python misc/answer-key-ceiling/verb_ceiling_v0.py
Writes corruption pairs to corruptions_v0.jsonl next to this file for audit.
"""

import argparse
import json
import random
import re
from pathlib import Path

from sacrebleu.metrics import CHRF

HERE = Path(__file__).parent
EVAL = Path("data/data-mixture/eval/samayik-eval.json")

CHRF6 = CHRF()                 # campaign metric: char order 6, beta 2
CHRFPP = CHRF(word_order=2)    # chrF++

DANDA = "।"  # ।
PUNCT = DANDA + "॥" + ",.!?;:\"'()[]{}—–-…‘’“”"

# Tokens that mark a row as Hindi rather than Sanskrit prose.
HINDI_MARKERS = {"है", "हैं", "था", "थे", "थी", "का", "की", "के", "को", "में",
                 "से", "पर", "और", "नहीं", "यह", "वह", "इस", "उस", "लिए",
                 "करना", "होता", "होती", "होते", "हुआ", "हुए", "गया", "गई"}

# Never treat these as verbs (quotative particle, common bare -ti/-tu nominals).
BLOCKLIST = {"इति", "गति", "मति", "स्थिति", "नीति", "रीति", "भक्ति", "शक्ति",
             "शान्ति", "क्रान्ति", "प्राप्ति", "सम्पत्ति", "विपत्ति", "वस्तु",
             "हेतु", "धातु", "सेतु", "ऋतु", "तन्तु", "साधु", "अति", "प्रति",
             "सन्ततिः", "सन्तति", "आकृति", "प्रकृति", "संस्कृति", "स्मृति",
             "कृति", "जाति", "पंक्ति", "व्यक्ति", "युक्ति", "उक्ति", "भूमिका"}

# Irregular (athematic) number flips where the naive suffix swap would coin a
# fake form. Kept to the high-frequency prose verbs.
IRREGULAR = {
    "अस्ति": "सन्ति", "सन्ति": "अस्ति",
    "नास्ति": "न सन्ति", "अस्मि": "स्मः", "स्मः": "अस्मि",
    "करोति": "कुर्वन्ति", "कुर्वन्ति": "करोति",
    "करोमि": "कुर्मः", "कुर्मः": "करोमि",
    "कुरुते": "कुर्वते", "कुर्वते": "कुरुते",
    "शक्नोति": "शक्नुवन्ति", "शक्नुवन्ति": "शक्नोति",
    "शक्नोमि": "शक्नुमः", "शक्नुमः": "शक्नोमि",
    "ददाति": "ददति", "ददति": "ददाति",
    "दधाति": "दधति", "जानाति": "जानन्ति", "जानन्ति": "जानाति",
    "जानामि": "जानीमः", "याति": "यान्ति", "यान्ति": "याति",
    "एति": "यन्ति", "ब्रवीति": "ब्रुवन्ति", "आह": "आहुः",
    "अस्तु": "सन्तु", "सन्तु": "अस्तु", "करोतु": "कुर्वन्तु",
    "कुर्वन्तु": "करोतु", "नुदन्तु": "नुदतु",
    "चिन्वन्तु": "चिनोतु", "शृण्वन्तु": "शृणोतु", "कुर्वते": "कुरुते",
    "भवेत्": "भवेयुः", "स्यात्": "स्युः", "कुर्यात्": "कुर्युः",
}

DEV_CONSONANT = re.compile(r"[क-हक़-य़]$")  # plain consonant, inherent -a-

# (ending, replacement, needs_clause_final). Longest patterns first; the
# preceding character must be a plain consonant (thematic stem) so the swap
# provably yields the true paradigm sibling.
SWAPS = [
    ("न्ति", "ति", False), ("न्ते", "ते", False), ("न्तु", "तु", False),
    ("ामः", "ामि", False), ("ामि", "ामः", False),
    ("ावः", "ामि", False), ("ामहे", "े", False),
    ("ेयुः", "ेत्", False), ("ेत्", "ेयुः", False),
    ("ेरन्", "ेत्", False),
    ("ति", "न्ति", True), ("ते", "न्ते", True), ("तु", "न्तु", True),
]


def flip_token(tok: str, clause_final: bool):
    """Return the number-flipped form of tok, or None if not confidently a verb."""
    if len(tok) < 3 or tok in BLOCKLIST:
        return None
    if tok.endswith("चेत्"):          # cet "if" particle, often sandhi-fused
        return None
    if tok in IRREGULAR:
        return IRREGULAR[tok]
    if "-" in tok:                     # hyphenated compound verb (klik-kurvantu)
        head, _, tail = tok.rpartition("-")
        if tail in IRREGULAR:
            return head + "-" + IRREGULAR[tail]
    for ending, repl, needs_final in SWAPS:
        if not tok.endswith(ending) or len(tok) - len(ending) < 2:
            continue
        if needs_final and not clause_final:
            continue
        stem = tok[: -len(ending)]
        # Thematic check: stem must end in a plain consonant (inherent a).
        # Rejects karoti (-o-), dadaati (-aa-), shaknoti (-no-), virama stems.
        # Also reject class-5/8 plural stems (-nv-/-Nv-), whose singular
        # rebuilds the stem (cinvanti -> cinoti), unless mapped above.
        if not DEV_CONSONANT.search(stem) or stem.endswith(("न्व", "ण्व", "ुव", "र्व")):
            return None
        return stem + repl
    return None


def corrupt_sentence(sa: str, mode: str = "flip"):
    """Corrupt every confidently-identified finite verb; return (text, n, pairs)."""
    toks = sa.split()
    out, pairs = [], []
    for i, raw in enumerate(toks):
        core = raw.strip(PUNCT)
        trail_start = raw.find(core) + len(core) if core else len(raw)
        lead = raw[: raw.find(core)] if core else raw
        trail = raw[trail_start:]
        clause_final = (i == len(toks) - 1) or raw.endswith((DANDA, "।।", "॥")) \
            or trail.strip("'\"‘’“”()").startswith(DANDA)
        flipped = flip_token(core, clause_final) if core else None
        if flipped:
            if mode == "delete":
                flipped = ""
            pairs.append((core, flipped))
            piece = lead + flipped + trail
            if piece:
                out.append(piece)
        else:
            out.append(raw)
    return " ".join(out), len(pairs), pairs


def is_hindi(sa: str) -> bool:
    toks = {t.strip(PUNCT) for t in sa.split()}
    return len(toks & HINDI_MARKERS) >= 2


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corruption", default="flip", choices=["flip", "delete"],
                    help="flip = number-flip minimal pair; delete = drop the verb "
                         "token entirely (worst case for verb-related chrF mass)")
    args = ap.parse_args()

    refs = json.loads(EVAL.read_text())
    rows = []
    n_hindi = 0
    for r in refs:
        sa = " ".join(r["sa"].split())
        if is_hindi(sa):
            n_hindi += 1
            rows.append({"sa": sa, "corrupted": sa, "n": 0, "pairs": [], "hindi": True})
            continue
        corrupted, n, pairs = corrupt_sentence(sa, args.corruption)
        rows.append({"sa": sa, "corrupted": corrupted, "n": n, "pairs": pairs,
                     "hindi": False})

    covered = [r for r in rows if r["n"] > 0]
    n_verbs = sum(r["n"] for r in rows)

    sent_scores = [CHRF6.sentence_score(r["corrupted"], [r["sa"]]).score for r in covered]
    sent_scores.sort()
    n = len(sent_scores)
    mean = sum(sent_scores) / n

    corp_cov = CHRF6.corpus_score([r["corrupted"] for r in covered],
                                  [[r["sa"] for r in covered]]).score
    corp_cov_pp = CHRFPP.corpus_score([r["corrupted"] for r in covered],
                                      [[r["sa"] for r in covered]]).score
    corp_all = CHRF6.corpus_score([r["corrupted"] for r in rows],
                                  [[r["sa"] for r in rows]]).score
    corp_all_pp = CHRFPP.corpus_score([r["corrupted"] for r in rows],
                                      [[r["sa"] for r in rows]]).score

    print(f"corruption mode: {args.corruption}")
    print(f"refs: {len(rows)}  hindi-excluded: {n_hindi}  "
          f"covered (>=1 verb corrupted): {len(covered)}  verbs corrupted: {n_verbs}")
    print(f"\n== covered subset (n={len(covered)}) — every identified verb mis-inflected ==")
    print(f"corpus chrF  : {corp_cov:.2f}   corpus chrF++: {corp_cov_pp:.2f}")
    print(f"sentence chrF: mean {mean:.2f}  median {sent_scores[n // 2]:.2f}  "
          f"p10 {sent_scores[n // 10]:.2f}  min {sent_scores[0]:.2f}")
    print(f"\n== all 750 (uncovered pass through verbatim) ==")
    print(f"corpus chrF  : {corp_all:.2f}   corpus chrF++: {corp_all_pp:.2f}")

    with open(HERE / f"corruptions_v0_{args.corruption}.jsonl", "w") as f:
        for r in rows:
            if r["n"]:
                f.write(json.dumps({"sa": r["sa"], "corrupted": r["corrupted"],
                                    "pairs": r["pairs"]}, ensure_ascii=False) + "\n")

    print("\n== audit sample (25 random corruptions) ==")
    rng = random.Random(42)
    flat = [(p, r["sa"]) for r in covered for p in r["pairs"]]
    for (orig, flip), sa in rng.sample(flat, min(25, len(flat))):
        print(f"  {orig} -> {flip}   |  {sa[:80]}")


if __name__ == "__main__":
    main()
