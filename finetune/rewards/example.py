"""Placeholder reward — replace with real rewards, keeping this exact shape.

A future vidyut-based reward would look like:

    from finetune.prompts import extract_answer

    @register("vp_exact_match")
    def vp_exact_match(prompts, completions, gold_devanagari, **kwargs):
        out = []
        for completion, golds in zip(completions, gold_devanagari):
            answer = extract_answer(completion)
            out.append(1.0 if answer in set(golds) else 0.0)
        return out
"""

from finetune.rewards import register


@register("example")
def example(prompts: list[str], completions: list[str], **kwargs) -> list[float]:
    """Placeholder: every completion gets reward 0.0."""
    return [0.0] * len(completions)
