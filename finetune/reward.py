"""The verifiable reward: completion text -> score in [0, 1].

    reward = 0.15 * format + 0.85 * task

Closed tasks (grammar QA) are exact-match against the Lean-exported gold
forms. Open tasks (translation, composition) are judged structurally by the
Lean checker: weighted grammar components x content constraints x length
damping — multiplicative, so prompt-ignoring or word-salad outputs score
near the floor (this shape survived an adversarial red-team in an earlier
iteration of the project; see the report).
"""

import difflib
import json
import re
import unicodedata

from .lean import check

_ANS = re.compile(r"<ans>(.*?)</ans>", re.DOTALL | re.IGNORECASE)

GRAMMAR_WEIGHTS = {"words": 0.40, "clauses": 0.15, "subject": 0.20,
                   "adjective": 0.10, "object": 0.15}

SYSTEM = ("Reasoning: low\n\nYou are an expert Sanskrit grammarian. Answer "
          "precisely, in IAST transliteration (ā ī ū ṛ ṭ ḍ ṇ ñ ṅ ś ṣ ṃ ḥ). "
          "Put your final answer inside <ans></ans> tags: just the Sanskrit, "
          "nothing else inside the tags.")


def extract(completion: str) -> tuple[str, bool]:
    """The answer inside the LAST <ans></ans>; fallback = last nonempty line."""
    m = _ANS.findall(completion)
    if m:
        return m[-1].strip(), True
    lines = [l.strip(" *`#") for l in completion.strip().splitlines() if l.strip()]
    return (lines[-1] if lines else ""), False


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s.strip().lower())
    return " ".join(re.sub(r"[।॥.,;:!?\"()\[\]]+", " ", s).split())


def grammar_score(components: dict) -> float:
    return sum(w * bool(components.get(k)) for k, w in GRAMMAR_WEIGHTS.items())


def reward(spec: dict, completion: str) -> dict:
    """spec: {'type': 'qa'|'translate'|'compose', 'gold': [...], 'specs': [...]}"""
    ans, fmt = extract(completion)
    ans = normalize(ans)
    if spec["type"] == "qa":
        golds = [normalize(g) for g in spec["gold"]]
        if ans in golds:
            task = 1.0
        else:  # graded near-miss credit, capped low (anti-gaming)
            best = max((difflib.SequenceMatcher(None, ans, g).ratio()
                        for g in golds), default=0)
            task = 0.25 * best if best >= 0.5 else 0.0
    else:
        n_tok = len(ans.split())
        if n_tok == 0:
            task = 0.0
        else:
            r = check(ans, tuple(spec["specs"]))
            grammar = grammar_score(r["components"])
            bits = r["constraints"]
            content = (sum(bits) / len(bits)) if bits else 1.0
            cap = 9 if spec["type"] == "translate" else 12
            damp = 1.0 if n_tok <= cap else max(0.05, cap / n_tok)
            task = grammar * (0.15 + 0.85 * content) * damp
    return {"reward": round(0.15 * fmt + 0.85 * task, 4),
            "task": round(task, 4), "format": fmt, "answer": ans}


def reward_from_answer_field(answer_json: str, completion: str) -> float:
    """Entry point for the GRPO trainer (spec rides in the dataset's
    `answer` field)."""
    try:
        return float(reward(json.loads(answer_json), completion)["reward"])
    except Exception:
        return 0.0
