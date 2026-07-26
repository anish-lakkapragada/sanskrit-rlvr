#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["sacrebleu"]
# ///
"""chrF / chrF++ comparison: Gemma 3 12B (OpenRouter) vs Gemma 4 (Gemini API)
on 10 difficult English -> Sanskrit (Devanagari) sentences.

Each sentence targets a specific grammatical construction and is
compositionally novel (not memorizable from parallel corpora). References
are single human-authored translations — chrF on free translation with one
reference is a rough signal only (string metrics correlate weakly with
human judgment for Sanskrit; see Mitrasamgraha 2026).

Usage:  uv run misc/chrf_compare.py
"""

import sys
import time

import gemma3_12b
import gemma4
from sacrebleu.metrics import CHRF

PROMPT = ("Translate into Sanskrit written in Devanagari script. "
          "Reply with ONLY the Sanskrit sentence, nothing else: {en}")

# (english, reference, construction being probed)
TESTS = [
    ("The two sisters will cook rice tomorrow.",
     "श्वो भगिन्यौ ओदनं पक्ष्यतः।", "dual subject + simple future"),
    ("The tired monk obtains water through patience.",
     "श्रान्तो मुनिः क्षान्त्या जलं लभते।", "atmanepada (labh) + instrumental"),
    ("Having seen the broken pot, the potter laughed.",
     "भग्नं घटं दृष्ट्वा कुम्भकारो जहास।", "absolutive + past"),
    ("The letter is being written by the doctor today.",
     "अद्य वैद्येन पत्रं लिख्यते।", "present passive (karmani)"),
    ("O king, protect the two villages!",
     "हे राजन्, ग्रामौ रक्ष।", "vocative + imperative + acc. dual"),
    ("When the rain falls, the farmers rejoice.",
     "वृष्टौ पतन्त्यां कृषकाः नन्दन्ति।", "locative absolute + plural agreement"),
    ("The man who speaks the truth is honored everywhere.",
     "यः सत्यं वदति स सर्वत्र पूज्यते।", "relative-correlative + passive"),
    ("This mountain is higher than that tree.",
     "अयं पर्वतः तस्माद् वृक्षाद् उच्चतरः।", "comparative + ablative of comparison"),
    ("The student wants to read the ancient book.",
     "छात्रः प्राचीनं पुस्तकं पठितुम् इच्छति।", "infinitive of purpose"),
    ("Five birds were seen by the child in the garden.",
     "उद्याने बालेन पञ्च पक्षिणः दृष्टाः।", "ppp + numeral + instrumental agent"),
]


# 0.2 not 0.0: greedy decoding can loop forever in Gemma 4's thinking channel.
TEMPERATURE = 0.2


def ask_gemma3(key: str, en: str) -> str:
    return gemma3_12b.generate(
        [{"role": "user", "content": PROMPT.format(en=en)}], key, temperature=TEMPERATURE)


def ask_gemma4(key: str, en: str) -> str:
    return gemma4.generate(
        [{"role": "user", "parts": [{"text": PROMPT.format(en=en)}]}], key, temperature=TEMPERATURE)


def with_retry(fn, *args, tries=3):
    for attempt in range(tries):
        try:
            return fn(*args)
        except (SystemExit, OSError) as e:  # timeouts, rate-limit blips
            if attempt == tries - 1:
                raise
            print(f"    retry {attempt + 1} after: {e}", file=sys.stderr)
            time.sleep(5)


def main() -> None:
    k3 = gemma3_12b.load_key()
    k4 = gemma4.load_key()
    chrf = CHRF()                # chrF  (character n-grams only)
    chrfpp = CHRF(word_order=2)  # chrF++ (adds word 1/2-grams)

    hyps3, hyps4, refs = [], [], []
    for i, (en, ref, construction) in enumerate(TESTS, 1):
        print(f"[{i}/{len(TESTS)}] {en}", file=sys.stderr)
        h3 = with_retry(ask_gemma3, k3, en).replace("\n", " ").strip()
        h4 = with_retry(ask_gemma4, k4, en).replace("\n", " ").strip()
        hyps3.append(h3)
        hyps4.append(h4)
        refs.append(ref)
        time.sleep(1)

    print(f"\n{'=' * 78}")
    print(f"{gemma3_12b.MODEL}  vs  {gemma4.MODEL}   (temperature {TEMPERATURE})")
    print(f"{'=' * 78}")
    for (en, ref, construction), h3, h4 in zip(TESTS, hyps3, hyps4):
        s3 = chrfpp.sentence_score(h3, [ref]).score
        s4 = chrfpp.sentence_score(h4, [ref]).score
        print(f"\nEN : {en}   [{construction}]")
        print(f"REF: {ref}")
        print(f"G3 : {h3}   (chrF++ {s3:.1f})")
        print(f"G4 : {h4}   (chrF++ {s4:.1f})")

    print(f"\n{'=' * 78}")
    print(f"corpus chrF   — gemma-3-12b: {chrf.corpus_score(hyps3, [refs]).score:.1f}"
          f"   gemma-4: {chrf.corpus_score(hyps4, [refs]).score:.1f}")
    print(f"corpus chrF++ — gemma-3-12b: {chrfpp.corpus_score(hyps3, [refs]).score:.1f}"
          f"   gemma-4: {chrfpp.corpus_score(hyps4, [refs]).score:.1f}")


if __name__ == "__main__":
    main()
