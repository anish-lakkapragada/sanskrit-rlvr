"""Pipeline step 8: mine real corpus sentences that live inside the fragment.

A DCS sentence qualifies when every token is analyzable by the v2 lexicon —
nominals in a covered cell (non-compound, real case), verbs in the finite
present indicative (non-passive), indeclinables and the three covered
pronouns — and the whole sentence, joined from unsandhied (pausa) tokens,
is judged Grammatical by the Lean checker. Each kept sentence carries its
per-token cell provenance from the DCS annotation (NOT from checker
analyses, which are ambiguous), so downstream corruption/cloze generators
know each token's true (lemma, cell).

The train/eval split is a stable hash of the sentence text: derived tasks
(post-edit, cloze, error-id) inherit their source sentence's split, so no
real sentence ever straddles the boundary.

Needs the corpus checkout (see README) and lean's built binaries.
Output: corpus/mined_sentences.tsv  (sent_id, split, source, sentence, tokens_json)
"""

import hashlib
import json
import re
import sys
from pathlib import Path

here = Path(__file__).parent
sys.path.insert(0, str(here.parent.parent))
from finetune.lean import check, lexicon  # noqa: E402

corpus_dir = Path("/tmp/dcs-sparse/dcs/data/conllu/files")
out_path = here / "corpus" / "mined_sentences.tsv"

CASES = {"Nom": "nom", "Acc": "acc", "Ins": "ins", "Dat": "dat",
         "Abl": "abl", "Gen": "gen", "Loc": "loc", "Voc": "voc"}
NUMS = {"Sing": "sg", "Dual": "du", "Plur": "pl"}
GENS = {"Masc": "m", "Fem": "f", "Neut": "n"}
# DCS lemma -> lexicon lemma (export prints the stem: bhagavant -> bhagavat;
# suppletive paśyati lives under dṛś)
LEMMA_MAP = {"bhagavant": "bhagavat", "jagant": "jagat", "paś": "dṛś"}
PRONOUNS = {"tad", "mad", "tvad"}   # enumerated in Sentence.lean
MIN_TOKENS, MAX_TOKENS = 3, 8


def feat(feats: str, key: str) -> str | None:
    m = re.search(rf"{key}=([^|]*)", feats)
    return m.group(1) if m else None


def pausa(form: str) -> str:
    """DCS Unsandhied keeps underlying finals (tatas, punar); the lexicon's
    citation forms are pausa (tataḥ, punaḥ)."""
    if form.endswith("s"):
        return form[:-1] + "ḥ"
    return form


def token_in_fragment(lemma: str, upos: str, feats: str, form: str, lex: dict
                      ) -> dict | None:
    """One token's fragment analysis {form, kind, lemma, slot}, or None."""
    lemma = LEMMA_MAP.get(lemma, lemma)
    form = pausa(form)
    case, num, gen = feat(feats, "Case"), feat(feats, "Number"), feat(feats, "Gender")
    if case and case != "Cpd" and num:
        c, n = CASES.get(case), NUMS.get(num)
        if not c or not n:
            return None
        if lemma in lex["noun"] and form in lex["noun"][lemma]["forms"].get((c, n), []):
            return {"form": form, "kind": "noun", "lemma": lemma, "slot": f"{c}:{n}"}
        if (lemma in lex["adj"] and gen in GENS
                and form in lex["adj"][lemma]["forms"].get((GENS[gen], c, n), [])):
            return {"form": form, "kind": "adj", "lemma": lemma,
                    "slot": f"{GENS[gen]}:{c}:{n}"}
        if lemma in PRONOUNS:   # the checker enumerates their forms; it decides
            return {"form": form, "kind": "pron", "lemma": lemma, "slot": ""}
        return None
    if upos == "VERB":
        person = feat(feats, "Person")
        if (feat(feats, "Tense") == "Pres" and feat(feats, "Mood") == "Ind"
                and "Voice=Pass" not in feats and person and num in NUMS
                and lemma in lex["verb"]
                and form in lex["verb"][lemma]["forms"].get((person, NUMS[num]), [])):
            return {"form": form, "kind": "verb", "lemma": lemma,
                    "slot": f"{person}:{NUMS[num]}"}
        return None
    if form in lex["ind"]:
        return {"form": form, "kind": "ind", "lemma": form, "slot": ""}
    return None


def mine() -> list[dict]:
    lex = lexicon()
    candidates, seen = [], set()
    for f in sorted(corpus_dir.rglob("*.conllu")):
        source = f.parent.name
        tokens, ok = [], True

        def flush():
            nonlocal tokens, ok
            if ok and MIN_TOKENS <= len(tokens) <= MAX_TOKENS \
                    and any(t["kind"] == "verb" for t in tokens):
                sentence = " ".join(t["form"] for t in tokens)
                if sentence not in seen:
                    seen.add(sentence)
                    candidates.append({"source": source, "sentence": sentence,
                                       "tokens": tokens})
            tokens, ok = [], True

        for line in open(f, encoding="utf-8"):
            line = line.rstrip("\n")
            if not line:
                flush()
                continue
            if line[0] == "#":
                continue
            cols = line.split("\t")
            if len(cols) < 10 or "-" in cols[0]:
                continue
            if not ok:
                continue
            m = re.search(r"Unsandhied=([^|]*)", cols[9])
            if not m or not m.group(1):
                ok = False
                continue
            t = token_in_fragment(cols[2], cols[3], cols[5], m.group(1), lex)
            if t is None:
                ok = False
            else:
                tokens.append(t)
        flush()
    return candidates


def main():
    candidates = mine()
    print(f"lemma+form-filtered candidates: {len(candidates)}")
    kept = []
    for c in candidates:
        if check(c["sentence"])["grammatical"]:
            split = "eval" if int(hashlib.md5(
                c["sentence"].encode()).hexdigest()[:8], 16) % 5 == 0 else "train"
            kept.append({**c, "split": split})
    n_eval = sum(1 for k in kept if k["split"] == "eval")
    print(f"checker-verified: {len(kept)} ({100 * len(kept) / len(candidates):.0f}%)"
          f" -> train {len(kept) - n_eval} / eval {n_eval}")
    with open(out_path, "w", encoding="utf-8") as out:
        out.write("sent_id\tsplit\tsource\tsentence\ttokens_json\n")
        for i, k in enumerate(kept):
            out.write(f"s{i}\t{k['split']}\t{k['source']}\t{k['sentence']}\t"
                      f"{json.dumps(k['tokens'], ensure_ascii=False)}\n")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
