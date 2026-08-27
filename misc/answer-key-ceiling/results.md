# Answer-key ceiling (v0, preliminary): what is verb morphology worth to chrF on Samayik?

**Question.** Our whole campaign tested "morphology skill → better translation" by watching
Samayik chrF. That assumes chrF actually pays for correct verb inflection. This experiment
measures that assumption directly, with zero model calls: corrupt ONLY the finite-verb
inflection of the 750 eval references (number flip, singular↔plural — a MorphEval-style
single-feature minimal pair) and score corrupted-reference against true reference. The
result is the score of a translation that is *perfect in every way except every identified
verb is inflected wrong* — an upper bound on what verb morphology can ever be worth here.

## Result

| corruption | view | chrF | chrF++ |
|---|---|---|---|
| wrong inflection (number flip) | covered subset (368 refs, all 447 identified verbs wrong) | **92.91** | 90.98 |
| wrong inflection (number flip) | all 750 refs (uncovered pass through verbatim) | **96.05** | 95.03 |
| verb DELETED entirely (worst case) | covered subset | 86.10 | 86.20 |
| verb DELETED entirely (worst case) | all 750 refs | 92.37 | 92.45 |

Sentence-level chrF on the covered subset (flip): mean 91.16, median 92.77, p10 83.86,
min 51.81 (~1.2 corrupted verbs per sentence → **~7 chrF per all-verbs-wrong sentence**, at
the top of the scale). The delete variant bounds the *entire* chrF mass of the verbs
themselves: even removing every identified verb outright costs only ~7.6 corpus points.

## Why this closes the case

- The **never-achievable extreme** — a model going from *every verb inflected wrong* to
  *every verb inflected right* — is worth ≈ **4 corpus chrF points** (7 on the covered half).
- A realistic training effect is a fraction of that. GRPO-r3 raised drill accuracy by
  +16.3pp pass@1; even if that mapped 1:1 into translation verb accuracy (+16% of verbs),
  the corpus-chrF bound is ≈ **0.6 points** — smaller than a single arm's 95% CI half-width
  (±1.3–1.5) and than the arm-to-arm chrF scatter in the mixture grid (~1–2).
- And this bound is computed at the top of the scale (reference vs reference); at our
  models' operating point (~41 chrF, where n-gram overlap is already sparse), the marginal
  chrF cost of one wrong inflection is smaller still.

**Conclusion (preliminary): the signal the campaign hunted was sub-noise by construction of
the metric.** chrF on Samayik cannot detect verb-morphology transfer, even a perfect one.
This is the LLM-scale, per-dataset version of Dalvi et al. 2017 (real morphology injection
moved BLEU 0.2–0.6) + Kocmi et al. 2021 (deltas that small don't track humans).

## Method (v0 heuristic — half-hour version)

`verb_ceiling_v0.py`: identify finite verbs by high-precision tiṅanta ending patterns;
flip grammatical number where the string swap provably yields the real paradigm sibling
(thematic stems: गच्छति→गच्छन्ति); explicit irregular map for common athematic verbs
(अस्ति↔सन्ति, करोति↔कुर्वन्ति, चिन्वन्तु→चिनोतु, …); short endings (-ति/-ते/-तु) additionally
require clause-final position; blocklist for इति/‑ति nominals/चेत्; 39 Hindi rows found in
samayik-eval excluded (data-quality footnote for the eval set). Corruption pairs in
`corruptions_v0.jsonl`; two 25-sample manual audits after patches: all pairs valid.

## Caveats / v1

- Recall is deliberately conservative: sandhi-fused and participial-style refs go
  uncounted, so the covered-subset number is the honest per-sentence unit; higher recall
  (vidyut-kosha identification + vidyut-prakriya sibling generation) would raise coverage,
  not the per-verb cost.
- Number flip only; person/tense flips change a comparable number of characters, so the
  chrF arithmetic is essentially unchanged.
- v1 (vidyut-verified minimal pairs, ~half a day) would make every corruption a certified
  real form for the writeup.
