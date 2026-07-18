"""RLVR against a Lean formalization of Sanskrit — all the Python in one file.

The linguistics live entirely in lean/ (the formalization is the verifier);
this file only generates tasks from Lean's exported lexicon, turns Lean's
judgments into a scalar reward, and runs evaluation/snapshots.

  python rlvr.py data                        build train/valid/eval sets
  python rlvr.py eval --tag base [...]       evaluate a model on the eval set
  python rlvr.py snapshots                   probe every training checkpoint

Reward shape (red-teamed in the previous iteration of this project):
  0.15 * format + 0.85 * task, where open-ended tasks are
  grammar * (0.15 + 0.85 * content) * length_damping — multiplicative, so
  prompt-ignoring or word-salad outputs score near the floor.
"""

import argparse
import difflib
import json
import random
import re
import subprocess
import unicodedata
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHECK = ROOT / "lean" / ".lake" / "build" / "bin" / "check"
EXPORT = ROOT / "lean" / ".lake" / "build" / "bin" / "export"

SYSTEM = ("Reasoning: low\n\nYou are an expert Sanskrit grammarian. Answer "
          "precisely, in IAST transliteration (ā ī ū ṛ ṭ ḍ ṇ ñ ṅ ś ṣ ṃ ḥ). "
          "Put your final answer inside <ans></ans> tags: just the Sanskrit, "
          "nothing else inside the tags.")

CASE_NAMES = {"nom": "nominative", "acc": "accusative", "ins": "instrumental",
              "dat": "dative", "abl": "ablative", "gen": "genitive",
              "loc": "locative", "voc": "vocative"}
NUM_NAMES = {"sg": "singular", "du": "dual", "pl": "plural"}
PERSON_NAMES = {"3": "third", "2": "second", "1": "first"}

# --- the Lean side ---------------------------------------------------------

@lru_cache(maxsize=1)
def lexicon():
    """Parse `lake exe export`: the single source of truth for forms.
    Adjective forms are keyed by (gender, case, number); everything else
    by (slot1, slot2)."""
    out = subprocess.run([EXPORT], capture_output=True, text=True).stdout
    lex = {"noun": {}, "adj": {}, "verb": {}, "ind": {}}
    for line in out.splitlines():
        kind, lemma, extra, gloss, slot1, slot2, form = line.split("\t")
        e = lex[kind].setdefault(lemma, {"gloss": gloss, "extra": extra, "forms": {}})
        key = (extra, slot1, slot2) if kind == "adj" else (slot1, slot2)
        e["forms"].setdefault(key, []).append(form)
    return lex


@lru_cache(maxsize=100_000)
def lean_check(sentence: str, specs: tuple[str, ...] = ()) -> dict:
    """One call into the formalization: five judgments + constraint bits."""
    r = subprocess.run([CHECK, sentence, *specs], capture_output=True, text=True)
    m = dict(kv.split("=", 1) for kv in r.stdout.strip().split(" ") if "=" in kv)
    return {
        "grammatical": r.returncode == 0,
        "components": {k: m.get(k) == "1"
                       for k in ("words", "verb", "subject", "adjective", "object")},
        "reqs": [b == "1" for b in m.get("reqs", "").split(",") if b],
        "lemmas": [l for l in m.get("lemmas", "").split(",") if l],
    }

# --- tasks ------------------------------------------------------------------

_PLURAL = {"man": "men", "wife": "wives"}
_NO_PLURAL = {"knowledge", "truth", "water", "peace", "fame", "learning",
              "Rāma", "earth", "moon"}

def _plural(g):
    if g in _PLURAL: return _PLURAL[g]
    if g.endswith("y") and g[-2] not in "aeiou": return g[:-1] + "ies"
    if g.endswith(("s", "sh", "ch", "x")): return g + "es"
    return g + "s"

def _v3sg(g):
    if g.endswith(("s", "sh", "ch", "x", "o")): return g + "es"
    return g + "s"


# glosses that read naturally as "in the X"
_LOC_OK = {"village", "forest", "house", "city", "field", "mountain",
           "river", "school", "road", "world"}


def make_tasks(n: int, seed: int) -> list[dict]:
    """Harder mix (v2): translation gives NO vocabulary hints (the model must
    know gloss->lemma), subjects may carry an adjective (gender agreement),
    intransitives may take a locative adjunct, and composition requires four
    words including an adjective. Verifiable by Lean; not enumerable enough
    for supervised training to saturate — which is where RL earns its keep."""
    lex = lexicon()
    rng = random.Random(seed)
    nouns = [(l, e) for l, e in lex["noun"].items()]
    verbs = [(l, e) for l, e in lex["verb"].items() if l not in ("as", "bhū")]
    adjs = [(l, e) for l, e in lex["adj"].items()]
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
            ref_parts, en_subj = [], None
            al = None
            if rng.random() < 0.45:
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
                loc = None
                if rng.random() < 0.6:
                    loc, le = rng.choice([x for x in nouns
                                          if x[1]["gloss"] in _LOC_OK and x[0] != sl])
                    specs.append(f"{loc}:loc:sg")
                    ref_parts.append(le["forms"][("loc", "sg")][0])
                    sent = f"The {en_subj} {v_en} in the {le['gloss']}."
                else:
                    sent = f"The {en_subj} {v_en}."
            ref_parts.append(v["forms"][("3", sn)][0])
            add({"type": "translate", "specs": specs, "gold": [],
                 "reference": " ".join(ref_parts),
                 "prompt": f'Translate into Sanskrit (one sentence): "{sent}"'})
        else:
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

# --- reward -----------------------------------------------------------------

_ANS = re.compile(r"<ans>(.*?)</ans>", re.DOTALL | re.IGNORECASE)
GRAMMAR_W = {"words": 0.40, "verb": 0.15, "subject": 0.20,
             "adjective": 0.10, "object": 0.15}


def extract(completion: str) -> tuple[str, bool]:
    m = _ANS.findall(completion)
    if m:
        return m[-1].strip(), True
    lines = [l.strip(" *`#") for l in completion.strip().splitlines() if l.strip()]
    return (lines[-1] if lines else ""), False


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s.strip().lower())
    return " ".join(re.sub(r"[।॥.,;:!?\"()\[\]]+", " ", s).split())


def reward(spec: dict, completion: str) -> dict:
    ans, fmt = extract(completion)
    ans = _norm(ans)
    if spec["type"] == "qa":
        golds = [_norm(g) for g in spec["gold"]]
        if ans in golds:
            task = 1.0
        else:
            best = max((difflib.SequenceMatcher(None, ans, g).ratio()
                        for g in golds), default=0)
            task = 0.25 * best if best >= 0.5 else 0.0
    else:
        n_tok = len(ans.split())
        if not ans or n_tok == 0:
            task = 0.0
        else:
            r = lean_check(ans, tuple(spec["specs"]))
            grammar = sum(GRAMMAR_W[k] * v for k, v in r["components"].items())
            content = (sum(r["reqs"]) / len(r["reqs"])) if r["reqs"] else 1.0
            cap = 9 if spec["type"] == "translate" else 12
            damp = 1.0 if n_tok <= cap else max(0.05, cap / n_tok)
            task = grammar * (0.15 + 0.85 * content) * damp
    return {"reward": round(0.15 * fmt + 0.85 * task, 4),
            "task": round(task, 4), "format": fmt, "answer": ans}

# --- CLI: data / eval / snapshots --------------------------------------------

MODEL = "mlx-community/Qwen3-4B-Instruct-2507-4bit"


def _splits():
    tasks = make_tasks(1000 + 64 + 150, seed=42)
    return {"eval": tasks[:150], "valid": tasks[150:214], "train": tasks[214:]}


def cmd_data(args):
    out = ROOT / "training" / "data"
    out.mkdir(parents=True, exist_ok=True)
    splits = _splits()
    for name, ts in splits.items():
        with (out / f"{name}.jsonl").open("w") as f:
            for t in ts:
                row = {"prompt": t["prompt"], "system": SYSTEM, "type": t["type"],
                       "answer": json.dumps({"type": t["type"], "gold": t["gold"],
                                             "specs": t["specs"]}, ensure_ascii=False)}
                if name == "eval":
                    row["reference"] = t["reference"]
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print({k: len(v) for k, v in splits.items()})


def cmd_data_sft(args):
    """SFT cold-start data: the same train/valid tasks, answered by the
    engine's own reference answers (still zero human labels)."""
    out = ROOT / "training" / "data_sft"
    out.mkdir(parents=True, exist_ok=True)
    splits = _splits()
    for name in ("train", "valid"):
        with (out / f"{name}.jsonl").open("w") as f:
            for t in splits[name]:
                f.write(json.dumps({"messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": t["prompt"]},
                    {"role": "assistant", "content": f"<ans>{t['reference']}</ans>"},
                ]}, ensure_ascii=False) + "\n")
    print("sft data written")


def _load_model(model, adapter):
    from mlx_lm import load
    return load(model, adapter_path=adapter)


def _generate(model, tok, system, prompt, max_tokens=384, temp=0.0):
    from mlx_lm import generate
    kwargs = {}
    if temp > 0:  # sampled eval — the regime RL actually optimizes
        from mlx_lm.sample_utils import make_sampler
        kwargs["sampler"] = make_sampler(temp=temp)
    p = tok.apply_chat_template(
        [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        add_generation_prompt=True, tokenize=False)
    return generate(model, tok, prompt=p, max_tokens=max_tokens, verbose=False, **kwargs)


def cmd_eval(args):
    from sacrebleu.metrics import CHRF
    if args.temp > 0:
        import mlx.core as mx
        mx.random.seed(7)
    model, tok = _load_model(args.model, args.adapter)
    rows = [json.loads(l) for l in (ROOT / "training/data/eval.jsonl").open()]
    if args.limit:
        rows = rows[:args.limit]
    recs = []
    for i, t in enumerate(rows):
        completion = _generate(model, tok, t["system"], t["prompt"], temp=args.temp)
        rb = reward(json.loads(t["answer"]), completion)
        spec = json.loads(t["answer"])
        grammatical = (spec["type"] != "qa" and rb["answer"]
                       and lean_check(rb["answer"], ())["grammatical"])
        recs.append({**t, "completion": completion, **rb,
                     "grammatical": bool(grammatical)})
        if (i + 1) % 25 == 0:
            print(f"{i+1}/{len(rows)} mean={sum(r['reward'] for r in recs)/len(recs):.3f}",
                  flush=True)
    mean = lambda xs: sum(xs) / len(xs) if xs else 0.0
    sent = [r for r in recs if r["type"] != "qa"]
    qa = [r for r in recs if r["type"] == "qa"]
    chrf = CHRF(word_order=2)
    summary = {
        "tag": args.tag, "model": args.model, "adapter": args.adapter,
        "n": len(recs),
        "mean_reward": round(mean([r["reward"] for r in recs]), 4),
        "compile_rate": round(mean([1.0 * r["grammatical"] for r in sent]), 4),
        "qa_exact": round(mean([1.0 * (r["task"] == 1.0) for r in qa]), 4),
        "format_rate": round(mean([1.0 * r["format"] for r in recs]), 4),
        "chrf_pp": round(chrf.corpus_score(
            [r["answer"] for r in recs], [[r["reference"] for r in recs]]).score, 2),
    }
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / f"eval_{args.tag}.json").write_text(
        json.dumps({"summary": summary, "records": recs}, ensure_ascii=False, indent=1))
    print(json.dumps(summary, indent=2))


PROBES = [
    'Translate into Sanskrit (one sentence): "The beautiful girl obtains the garland."',
    'Translate into Sanskrit (one sentence): "The heroes protect the village."',
    'Translate into Sanskrit (one sentence): "The young sage dwells in the forest."',
    'Translate into Sanskrit (one sentence): "The teacher drinks the water."',
    "Write one grammatically correct Sanskrit sentence using all of these words "
    "(inflect as needed): gam ('to go'), putra ('son'), nagara ('city'), nava ('new').",
    "Write one grammatically correct Sanskrit sentence using all of these words "
    "(inflect as needed): labh ('to obtain'), kanyā ('girl'), mālā ('garland'), "
    "śveta ('white').",
    "What is the instrumental singular of the Sanskrit noun rāma ('Rāma')?",
    "What is the genitive plural of the Sanskrit noun guru ('teacher')?",
    "What is the present tense, third person plural of the Sanskrit verb kṛ ('to do')?",
    "What is the locative singular of the Sanskrit noun agni ('fire')?",
]


def cmd_snapshots(args):
    ckpts = sorted((ROOT / "training" / "adapters").glob("0*_adapters.safetensors"))
    out = ROOT / "results" / "snapshots.jsonl"
    done = {(r["iteration"], r["probe"]) for r in map(json.loads, out.open())} \
        if out.exists() else set()
    points = [(0, None)] + [(int(c.name.split("_")[0]), c) for c in ckpts]
    import shutil, tempfile
    for it, ckpt in points:
        adapter = None
        if ckpt is not None:
            tmp = Path(tempfile.mkdtemp())
            shutil.copy(ckpt, tmp / "adapters.safetensors")
            shutil.copy(ROOT / "training/adapters/adapter_config.json", tmp)
            adapter = str(tmp)
        if all((it, p) in done for p in PROBES):
            continue
        model, tok = _load_model(args.model, adapter)
        with out.open("a") as f:
            for p in PROBES:
                if (it, p) in done:
                    continue
                completion = _generate(model, tok, SYSTEM, p)
                ans, _ = extract(completion)
                ok = lean_check(_norm(ans), ())["grammatical"] if ans else False
                f.write(json.dumps({"iteration": it, "probe": p, "answer": ans,
                                    "grammatical": bool(ok)}, ensure_ascii=False) + "\n")
        del model
        print(f"snapshot @ iter {it} done", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("data")
    sub.add_parser("data-sft")
    e = sub.add_parser("eval")
    e.add_argument("--tag", required=True)
    e.add_argument("--model", default=MODEL)
    e.add_argument("--adapter", default=None)
    e.add_argument("--limit", type=int, default=None)
    e.add_argument("--temp", type=float, default=0.0)
    s = sub.add_parser("snapshots")
    s.add_argument("--model", default=MODEL)
    args = ap.parse_args()
    {"data": cmd_data, "data-sft": cmd_data_sft, "eval": cmd_eval,
     "snapshots": cmd_snapshots}[args.cmd](args)
