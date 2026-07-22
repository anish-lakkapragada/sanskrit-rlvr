"""Pipeline step 9: the out-of-fragment benchmark — attested cloze.

Real sentences from classical texts that the fragment can NOT fully analyze
(at least one token fails the in-fragment test: an unknown lemma, a tense
beyond the present indicative, a compound member …), in which exactly one
token IS fully in-fragment. That token is blanked; the model must produce
it; grading is exact match against the attested form (plus the accepted
classical variants of the same paradigm cell). This measures whether learned
morphology survives contact with wild Sanskrit — no English references, no
Lean judgment at eval time, no way to game it.

Sources are restricted to classical-register texts (no Vedic saṃhitās or
brāhmaṇas, no technical nighaṇṭus). Needs the corpus checkout; writes
data/out_of_fragment/eval.jsonl (judge: "exact").
"""

import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

here = Path(__file__).parent
sys.path.insert(0, str(here.parent.parent))
from finetune.lean import lexicon                     # noqa: E402
from finetune.reward import SYSTEM                    # noqa: E402
from mine_sentences import token_in_fragment          # noqa: E402

corpus_dir = Path("/tmp/dcs-sparse/dcs/data/conllu/files")
out_path = here.parent.parent / "data" / "out_of_fragment" / "eval.jsonl"

ALLOWLIST = [
    # epic
    "Mahābhārata", "Rāmāyaṇa", "Harivaṃśa",
    # narrative prose / fable
    "Hitopadeśa", "Tantrākhyāyikā", "Kathāsaritsāgara", "Vetālapañcaviṃśatikā",
    "Śukasaptati", "Bṛhatkathāślokasaṃgraha", "Daśakumāracarita",
    # kāvya
    "Buddhacarita", "Saundarānanda", "Kumārasaṃbhava", "Kirātārjunīya",
    "Meghadūta", "Ṛtusaṃhāra", "Amaruśataka", "Śatakatraya", "Gītagovinda",
    # dharma / purāṇa
    "Manusmṛti", "Yājñavalkyasmṛti", "Devīmāhātmya",
]
MIN_TOKENS, MAX_TOKENS = 4, 12
PER_TEXT_CAP = 12
TARGET = 150
CANDIDATE_CAP = 500          # per text, to bound memory
KIND_EN = {"noun": "noun", "adj": "adjective", "verb": "verb"}


def sentences(path: Path):
    """Yield [(lemma, upos, feats, unsandhied), ...] per sentence."""
    sent = []
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line:
            if sent:
                yield sent
            sent = []
            continue
        if line[0] == "#":
            continue
        cols = line.split("\t")
        if len(cols) < 10 or "-" in cols[0]:
            continue
        m = re.search(r"Unsandhied=([^|]*)", cols[9])
        sent.append((cols[2], cols[3], cols[5], m.group(1) if m else None))
    if sent:
        yield sent


def display_tokens(sent, lex):
    """Hyphen-join compound runs into their head; analyze standalone tokens.
    Returns [(display_form, analysis_or_None, is_compound)] or None if any
    token lacks an unsandhied form."""
    out, buf = [], []
    for lemma, upos, feats, form in sent:
        if form is None or not form:
            return None
        if "Case=Cpd" in feats:
            buf.append(form)
            continue
        if buf:
            out.append(("-".join(buf) + "-" + form, None, True))
            buf = []
        else:
            out.append((form, token_in_fragment(lemma, upos, feats, form, lex),
                        False))
    if buf:                    # sentence ends inside a compound: malformed
        return None
    return out


def mine():
    lex = lexicon()
    rng = random.Random(0)
    by_text = defaultdict(list)
    texts = [t for t in ALLOWLIST if (corpus_dir / t).is_dir()]
    missing = set(ALLOWLIST) - set(texts)
    if missing:
        print(f"note: not in corpus checkout: {sorted(missing)}")
    for text in texts:
        for f in sorted((corpus_dir / text).rglob("*.conllu")):
            if len(by_text[text]) >= CANDIDATE_CAP:
                break
            for sent in sentences(f):
                disp = display_tokens(sent, lex)
                if disp is None or not MIN_TOKENS <= len(disp) <= MAX_TOKENS:
                    continue
                analyzed = [(i, a) for i, (fm, a, cpd) in enumerate(disp) if a]
                n_oof = sum(1 for fm, a, cpd in disp if a is None)
                if n_oof == 0:      # fully in-fragment: that's the other benchmark
                    continue
                maskable = [
                    (i, a) for i, a in analyzed
                    if a["kind"] in KIND_EN
                    and sum(1 for fm, _, _ in disp if fm == a["form"]) == 1]
                if not maskable:
                    continue
                # prefer nominals (the morphology axis under test)
                nominal = [x for x in maskable if x[1]["kind"] != "verb"]
                i, a = rng.choice(nominal or maskable)
                cell = tuple(a["slot"].split(":"))
                variants = lex[a["kind"]][a["lemma"]]["forms"].get(cell, [])
                if a["form"] not in variants:
                    continue
                blanked = " ".join("____" if j == i else fm
                                   for j, (fm, _, _) in enumerate(disp))
                by_text[text].append({
                    "blanked": blanked, "lemma": a["lemma"], "kind": a["kind"],
                    "gloss": lex[a["kind"]][a["lemma"]]["gloss"],
                    "gold": [a["form"]] + [v for v in variants if v != a["form"]],
                    "text": text})
                if len(by_text[text]) >= CANDIDATE_CAP:
                    break
    rows, i = [], 0
    for text in texts:
        pool = by_text[text]
        rng.shuffle(pool)
        for c in pool[:PER_TEXT_CAP]:
            rows.append(c)
    rng.shuffle(rows)
    rows = rows[:TARGET]
    out = []
    for i, c in enumerate(rows):
        prompt = (f'The following is a line of classical Sanskrit, written '
                  f'without sandhi and with compounds hyphenated: '
                  f'"{c["blanked"]}". Replace ____ with the correct form of '
                  f"the {KIND_EN[c['kind']]} {c['lemma']} ('{c['gloss']}'). "
                  "Output only that word.")
        out.append({"id": f"o{i}", "type": "cloze", "prompt": prompt,
                    "system": SYSTEM, "judge": "exact", "gold": c["gold"],
                    "specs": [], "reference": c["gold"][0],
                    "source": c["text"]})
    with open(out_path, "w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    per = defaultdict(int)
    for r in out:
        per[r["source"]] += 1
    print(f"wrote {out_path}: {len(out)} rows from {len(per)} texts")
    print("  " + ", ".join(f"{t}:{n}" for t, n in sorted(per.items())))


if __name__ == "__main__":
    mine()
