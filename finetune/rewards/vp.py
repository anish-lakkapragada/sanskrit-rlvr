"""VP task rewards: reward = 0.15 * format + 0.85 * content, in [0, 1].

Format score is BINARY (all-or-nothing): 1.0 iff the completion contains
exactly one well-formed <thinking>...</thinking> block AND exactly one
well-formed, non-empty <answer>...</answer> block, with the thinking block
before the answer block. Anything else -> 0.0.

Content score (the three variants differ only here):
- vp_exact:  1.0 if the extracted answer is one of the gold Devanagari
             forms, else 0.0
- vp_chrf:   max sentence-chrF against the gold list, scaled to 0-1
- vp_chrfpp: same with chrF++ (word_order=2)

Content is computed from the <answer> extraction; if it fails, content = 0.
Both sides are NFC-normalized and stripped before comparison.

Self-test: uv run python -m finetune.rewards.vp
"""

import re
import unicodedata

from sacrebleu.metrics import CHRF

from finetune.prompts import extract_answer
from finetune.rewards import register

FORMAT_WEIGHT = 0.15
CONTENT_WEIGHT = 0.85

_CHRF = CHRF()
_CHRFPP = CHRF(word_order=2)

_THINKING_RE = re.compile(r"<thinking>(.*?)</thinking>", re.DOTALL)
_ANSWER_RE = re.compile(r"<answer>(.*?)</answer>", re.DOTALL)


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text).strip()


def format_score(completion: str) -> float:
    """1.0 iff exactly one <thinking> block and exactly one non-empty
    <answer> block exist, thinking before answer; else 0.0."""
    if not isinstance(completion, str):
        return 0.0
    thinkings = list(_THINKING_RE.finditer(completion))
    answers = list(_ANSWER_RE.finditer(completion))
    if len(thinkings) != 1 or len(answers) != 1:
        return 0.0
    if not answers[0].group(1).strip():
        return 0.0
    if thinkings[0].start() >= answers[0].start():
        return 0.0
    return 1.0


def _content_exact(answer: str | None, golds: list[str]) -> float:
    if not answer:
        return 0.0
    return 1.0 if _norm(answer) in {_norm(g) for g in golds} else 0.0


def _content_chrf(answer: str | None, golds: list[str], metric: CHRF) -> float:
    if not answer:
        return 0.0
    hyp = _norm(answer)
    return max(metric.sentence_score(hyp, [_norm(g)]).score for g in golds) / 100.0


def _combine(completions, gold_devanagari, content_fn) -> list[float]:
    rewards = []
    for completion, golds in zip(completions, gold_devanagari):
        fmt = format_score(completion)
        content = content_fn(extract_answer(completion), golds)
        rewards.append(FORMAT_WEIGHT * fmt + CONTENT_WEIGHT * content)
    return rewards


@register("vp_exact")
def vp_exact(prompts, completions, gold_devanagari, **kwargs) -> list[float]:
    return _combine(completions, gold_devanagari, _content_exact)


@register("vp_chrf")
def vp_chrf(prompts, completions, gold_devanagari, **kwargs) -> list[float]:
    return _combine(completions, gold_devanagari,
                    lambda a, g: _content_chrf(a, g, _CHRF))


@register("vp_chrfpp")
def vp_chrfpp(prompts, completions, gold_devanagari, **kwargs) -> list[float]:
    return _combine(completions, gold_devanagari,
                    lambda a, g: _content_chrf(a, g, _CHRFPP))


if __name__ == "__main__":
    golds = [["भवति"]]
    call = lambda fn, text, g=golds: fn([""], [text], gold_devanagari=g)[0]

    perfect = "<thinking>bhū, laṭ, 3sg</thinking>\n<answer>भवति</answer>"
    wrong = "<thinking>hm</thinking><answer>गच्छति</answer>"
    near = "<thinking>hm</thinking><answer>भवती</answer>"
    no_tags = "the answer is भवति"
    no_thinking = "<answer>भवति</answer>"
    two_answers = "<thinking>a</thinking><answer>भवति</answer><answer>भवति</answer>"
    wrong_order = "<answer>भवति</answer><thinking>a</thinking>"
    empty_answer = "<thinking>a</thinking><answer>  </answer>"

    assert call(vp_exact, perfect) == 1.0
    assert call(vp_chrf, perfect) == 1.0
    assert call(vp_chrfpp, perfect) == 1.0

    assert call(vp_exact, wrong) == FORMAT_WEIGHT
    assert FORMAT_WEIGHT < call(vp_chrf, wrong) < 1.0

    assert call(vp_exact, near) == FORMAT_WEIGHT
    # graded credit: near-miss (BavatI) must clearly outscore a wrong word
    assert call(vp_chrf, near) > call(vp_chrf, wrong) + 0.15
    assert call(vp_chrfpp, near) > call(vp_chrfpp, wrong) + 0.15

    assert call(vp_exact, no_tags) == 0.0
    assert call(vp_chrf, no_tags) == 0.0

    # format is binary: no thinking block -> format 0, but content still counts
    assert call(vp_exact, no_thinking) == CONTENT_WEIGHT
    assert call(vp_exact, two_answers) == 0.0      # extraction + format both fail
    # answer-before-thinking: format 0, but the (correct) answer still extracts
    assert format_score(wrong_order) == 0.0
    assert call(vp_exact, wrong_order) == CONTENT_WEIGHT
    assert call(vp_exact, empty_answer) == 0.0

    # multi-gold: matching ANY gold gives full content credit
    multi = [["एधाञ्चकृषे", "एधामासिषे", "एधाम्बभूविषे"]]
    assert call(vp_exact, "<thinking>x</thinking><answer>एधामासिषे</answer>", multi) == 1.0

    # batch shape
    batch = vp_chrfpp([""] * 3, [perfect, wrong, no_tags], gold_devanagari=golds * 3)
    assert len(batch) == 3 and batch[0] == 1.0 > batch[1] > batch[2] == 0.0

    print("vp rewards self-test passed")
    print(f"  perfect={call(vp_exact, perfect):.3f}  wrong(exact)={call(vp_exact, wrong):.3f}  "
          f"wrong(chrf)={call(vp_chrf, wrong):.3f}  near(chrf)={call(vp_chrf, near):.3f}")
