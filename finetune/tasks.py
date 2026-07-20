"""Task generation from the Lean lexicon export — and the data/ writer.

Three machine-checkable task families over the fragment's vocabulary:
  qa         inflect one form (exact-match against Lean-exported gold)
  translate  templated English sentence, no vocabulary hints; verified
             structurally (right lemmas in the right cases, by Lean)
  compose    one sentence using four required words (verb, two nouns, an
             adjective) — grammar by Lean, coverage by constraint bits

`python -m finetune.tasks` regenerates everything under data/in_fragment/.
All splits come from one deduplicated stream, so no eval prompt ever appears
in a training file. The hand-curated data/out_of_fragment/eval.jsonl (real
classical Sanskrit the grammar does not model) is never touched.
"""

import json
import random
from pathlib import Path

from .lean import ROOT, lexicon
from .reward import SYSTEM

CASE_NAMES = {"nom": "nominative", "acc": "accusative", "ins": "instrumental",
              "dat": "dative", "abl": "ablative", "gen": "genitive",
              "loc": "locative", "voc": "vocative"}
NUM_NAMES = {"sg": "singular", "du": "dual", "pl": "plural"}
PERSON_NAMES = {"3": "third", "2": "second", "1": "first"}

_IRREGULAR_PLURAL = {"man": "men", "wife": "wives", "child": "children"}
_NO_PLURAL = {"knowledge", "truth", "water", "peace", "fame", "learning",
              "Rāma", "earth", "moon", "Ganges", "radiance", "memory", "wind"}
_LOC_OK = {"village", "forest", "house", "city", "field", "mountain",
           "river", "school", "road", "world", "Ganges", "ocean", "battle"}


def _plural(g):
    if g in _IRREGULAR_PLURAL:
        return _IRREGULAR_PLURAL[g]
    if g.endswith("y") and g[-2] not in "aeiou":
        return g[:-1] + "ies"
    if g.endswith(("s", "sh", "ch", "x")):
        return g + "es"
    return g + "s"


def _v3sg(g):
    if g.endswith(("s", "sh", "ch", "x", "o")):
        return g + "es"
    if g.endswith("y") and g[-2] not in "aeiou":
        return g[:-1] + "ies"
    return g + "s"


def make_tasks(n: int, seed: int) -> list[dict]:
    lex = lexicon()
    rng = random.Random(seed)
    nouns = list(lex["noun"].items())
    verbs = [(l, e) for l, e in lex["verb"].items() if l not in ("as", "bhū")]
    adjs = list(lex["adj"].items())
    gender_of = {l: e["extra"] for l, e in nouns}
    tasks, seen = [], set()

    def add(t):
        if t["prompt"] not in seen:
            seen.add(t["prompt"])
            tasks.append(t)

    def adj_form(al, noun_lemma, num):
        return lex["adj"][al]["forms"][(gender_of[noun_lemma], "nom", num)][0]

    while len(tasks) < n:
        kind = rng.choices(["qa", "translate", "compose"], weights=[3, 4, 3])[0]
        if kind == "qa":
            if rng.random() < 0.5:
                lemma, e = rng.choice(nouns)
                case, num = rng.choice(list(CASE_NAMES)), rng.choice(list(NUM_NAMES))
                gold = e["forms"][(case, num)]
                q = (f"What is the {CASE_NAMES[case]} {NUM_NAMES[num]} of the "
                     f"Sanskrit noun {lemma} ('{e['gloss']}')?")
            else:
                lemma, e = rng.choice(verbs)
                p, num = rng.choice(list(PERSON_NAMES)), rng.choice(list(NUM_NAMES))
                gold = e["forms"][(p, num)]
                q = (f"What is the present tense, {PERSON_NAMES[p]} person "
                     f"{NUM_NAMES[num]} of the Sanskrit verb {lemma} "
                     f"('to {e['gloss']}')?")
            add({"type": "qa", "prompt": q, "gold": gold, "specs": [],
                 "reference": gold[0]})
        elif kind == "translate":
            vl, v = rng.choice(verbs)
            trans = v["extra"] == "t"
            sl, s = rng.choice(nouns)
            sn = "sg" if s["gloss"] in _NO_PLURAL else rng.choice(["sg", "pl"])
            specs = [f"{sl}:nom:{sn}", f"verb:{vl}:3:{sn}"]
            ref_parts = []
            if rng.random() < 0.45 and adjs:
                al, a = rng.choice(adjs)
                specs.append(al)
                ref_parts.append(adj_form(al, sl, sn))
                en_subj = f"{a['gloss']} {s['gloss'] if sn == 'sg' else _plural(s['gloss'])}"
            else:
                en_subj = s["gloss"] if sn == "sg" else _plural(s["gloss"])
            ref_parts.append(s["forms"][("nom", sn)][0])
            v_en = _v3sg(v["gloss"]) if sn == "sg" else v["gloss"]
            if trans:
                ol, o = rng.choice([x for x in nouns if x[0] != sl])
                on = "sg" if o["gloss"] in _NO_PLURAL else rng.choice(["sg", "pl"])
                specs.append(f"{ol}:acc:{on}")
                ref_parts.append(o["forms"][("acc", on)][0])
                o_en = o["gloss"] if on == "sg" else _plural(o["gloss"])
                sent = f"The {en_subj} {v_en} the {o_en}."
            else:
                if rng.random() < 0.6:
                    loc_pool = [x for x in nouns
                                if x[1]["gloss"] in _LOC_OK and x[0] != sl]
                    if loc_pool:
                        loc, le = rng.choice(loc_pool)
                        specs.append(f"{loc}:loc:sg")
                        ref_parts.append(le["forms"][("loc", "sg")][0])
                        sent = f"The {en_subj} {v_en} in the {le['gloss']}."
                    else:
                        sent = f"The {en_subj} {v_en}."
                else:
                    sent = f"The {en_subj} {v_en}."
            ref_parts.append(v["forms"][("3", sn)][0])
            add({"type": "translate", "specs": specs, "gold": [],
                 "reference": " ".join(ref_parts),
                 "prompt": f'Translate into Sanskrit (one sentence): "{sent}"'})
        else:
            if not adjs:
                continue
            vl, v = rng.choice(verbs)
            n1, e1 = rng.choice(nouns)
            n2, e2 = rng.choice([x for x in nouns if x[0] != n1])
            al, a = rng.choice(adjs)
            words = [(vl, f"to {v['gloss']}"), (n1, e1["gloss"]),
                     (n2, e2["gloss"]), (al, a["gloss"])]
            rng.shuffle(words)
            wl = ", ".join(f"{w} ('{g}')" for w, g in words)
            obj = ("acc", "sg") if v["extra"] == "t" else ("loc", "sg")
            ref = (f"{adj_form(al, n1, 'sg')} {e1['forms'][('nom', 'sg')][0]} "
                   f"{e2['forms'][obj][0]} {v['forms'][('3', 'sg')][0]}")
            add({"type": "compose", "specs": [vl, n1, n2, al], "gold": [],
                 "reference": ref,
                 "prompt": ("Write one grammatically correct Sanskrit sentence "
                            f"using all of these words (inflect as needed): {wl}.")})
    return tasks


# --- data/ writer -----------------------------------------------------------

def _spec_json(t):
    return json.dumps({"type": t["type"], "gold": t["gold"],
                       "specs": t["specs"]}, ensure_ascii=False)


def _write(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{path.relative_to(ROOT)}: {len(rows)}")


def main():
    stream = make_tasks(150 + 64 + 64 + 1000 + 1000, seed=42)
    eval_in, valid_sft, valid_grpo = stream[:150], stream[150:214], stream[214:278]
    train_sft, train_grpo = stream[278:1278], stream[1278:2278]

    def eval_row(t, i, judge):
        return {"id": f"e{i}", "type": t["type"], "prompt": t["prompt"],
                "system": SYSTEM, "judge": judge, "gold": t["gold"],
                "specs": t["specs"], "reference": t["reference"]}

    def sft_row(t):
        return {"messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": t["prompt"]},
            {"role": "assistant", "content": f"<ans>{t['reference']}</ans>"}]}

    def grpo_row(t):
        return {"prompt": t["prompt"], "system": SYSTEM, "type": t["type"],
                "answer": _spec_json(t)}

    _write(ROOT / "data/in_fragment/sft/train.jsonl",
           [sft_row(t) for t in train_sft])
    _write(ROOT / "data/in_fragment/sft/valid.jsonl",
           [sft_row(t) for t in valid_sft])
    _write(ROOT / "data/in_fragment/grpo/train.jsonl",
           [grpo_row(t) for t in train_grpo])
    _write(ROOT / "data/in_fragment/grpo/valid.jsonl",
           [grpo_row(t) for t in valid_grpo])
    _write(ROOT / "data/in_fragment/eval.jsonl",
           [eval_row(t, i, "lean+chrf") for i, t in enumerate(eval_in)])


if __name__ == "__main__":
    main()
