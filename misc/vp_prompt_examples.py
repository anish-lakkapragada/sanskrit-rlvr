"""Two offline prompt/answer examples, verified with vidyut 0.4.0.

Run from the repository root: .venv/bin/python misc/vp_prompt_examples.py
VP supplies forms and a valid trace. This file supplies English templates and
an explicit, example-specific trace corruption; it is not a general trace editor.
"""
import json

from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import (
    Dhatu, Gana, Lakara, Pada, Prayoga, Purusha, Vacana, Vyakarana,
)

VP = Vyakarana(log_steps=True)


def deva(slp1):
    return transliterate(slp1, Scheme.Slp1, Scheme.Devanagari)


def derive(dhatu, lakara):
    return VP.derive(Pada.Tinanta(
        dhatu=dhatu,
        lakara=lakara,
        prayoga=Prayoga.Kartari,
        purusha=Purusha.Prathama,
        vacana=Vacana.Eka,
    ))


def modification_example():
    # Exact SLP1 dictionary citation for gam, entry 01.1137.
    # This root is private generation metadata, absent from the public prompt.
    gam = Dhatu.mula(aupadeshika=r"ga\mx~", gana=Gana.Bhvadi)
    sources = sorted({deva(p.text) for p in derive(gam, Lakara.Lat)})
    answers = sorted({deva(p.text) for p in derive(gam, Lakara.Lan)})
    assert sources == ["गच्छति"]
    assert set(answers) == {"अगच्छत्", "अगच्छद्"}

    prompt = f"""Given the Sanskrit word {sources[0]} with these grammatical coordinates:

- Tense/mood: Present (Lat)
- Voice: Agentive (Kartari)
- Person: Third person (Prathama)
- Number: Singular (Eka)

Change the tense to imperfect past (Lan), preserving the verb's
meaning, voice, person, and number.

Return only the resulting Devanagari word."""
    return {"prompt": prompt, "accepted_answers": answers}


def correction_example():
    bhu = Dhatu.mula(aupadeshika="BU", gana=Gana.Bhvadi)
    paths = derive(bhu, Lakara.Lat)
    assert len(paths) == 1
    p = paths[0]

    # Extract three states from VP's actual history, omitting technical steps.
    i = next(i for i, step in enumerate(p.history) if step.code == "7.3.84")
    j = next(i for i, step in enumerate(p.history) if step.code == "6.1.78")
    assert i < j
    good = [list(p.history[i - 1].result), list(p.history[i].result),
            list(p.history[j].result)]
    assert good == [["BU", "a", "ti"], ["Bo", "a", "ti"], ["Bav", "a", "ti"]]

    # Introduce one error: guna o -> vrddhi O (SLP1 O means Sanskrit au).
    # Carry that error forward in this illustrative continuation.
    bad = [state.copy() for state in good]
    bad[1][0] = bad[1][0].replace("o", "O")
    bad[2][0] = bad[2][0].replace("av", "Av")

    def show(state):
        return " + ".join(deva(term) for term in state)

    prompt = f"""The following simplified derivation starts from the Sanskrit verbal
root (dhatu) {deva(bhu.aupadeshika)}, meaning "to be / become," in conjugation class 1.

Requested coordinates:
- Tense/mood: Present (Lat)
- Voice: Agentive (Kartari)
- Person: Third person (Prathama)
- Number: Singular (Eka)

Derivation trace, with technical marker-removal steps omitted:
1. Add the present-stem vowel अ and personal ending ति:
   {show(bad[0])}
2. Apply guna to the root vowel:
   {show(bad[1])}
3. Replace औ before the following vowel with आव्:
   {show(bad[2])}
4. Combine:
   {deva(''.join(bad[2]))}

One step introduces an error; subsequent steps may propagate it.

Identify the first incorrect step, explain the error, and provide
the corrected derivation from that point and the final Devanagari word."""

    answer = {
        "first_incorrect_step": 2,
        "explanation": "The guna of ऊ is ओ, not औ; औ is its vrddhi grade.",
        "corrected_steps": [
            f"2. Apply guna (ऊ → ओ): {show(good[1])}",
            f"3. Replace ओ before a vowel with अव्: {show(good[2])}",
            f"4. Combine: {deva(p.text)}",
        ],
        "final_answer": deva(p.text),
    }
    assert answer["final_answer"] == "भवति"
    assert deva(''.join(bad[2])) == "भावति"
    return {"prompt": prompt, "answer": answer}


if __name__ == "__main__":
    print(json.dumps({
        "modification": modification_example(),
        "correction": correction_example(),
    }, ensure_ascii=False, indent=2))
