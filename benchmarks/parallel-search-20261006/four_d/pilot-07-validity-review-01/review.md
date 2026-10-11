# Pilot07: bounded development validity review

**Coordinator disposition:** adopted as shared policy19 after independent source review and 38 passing scope tests. The baseline and proposal calculations below remain the immutable policy18 comparison; the current shared analysis agrees with the retained counts.

This review proposed one source-backed hold: six specified lexical entries whose initial intensive derivation takes VP trace rule 7.4.85 instead of the source-supported rī augmentation. The proposal comes from three direct printed controls plus explicit rule inference. It applies independently of model correctness. No shared policy, raw result, candidate membership, or paid protocol was changed here.

Both settled revision01 chunks were reviewed, totaling 2,400 development questions. No candidate model answers were read. The original result is **1,854/2,400 = 77.25% overall**, **1,854/2,381 = 77.8664% usable**, with 19 nonusable responses. The proposed hold affects 12 usable wrong responses and zero correct responses. If adopted, the result becomes **1,854/2,388 = 77.6382% overall**, **1,854/2,369 = 78.2609% usable**, with missing-response bounds **77.6382–78.4338%**. These are bounds from missing responses, not confidence intervals. The advance criterion still fails.

## Source-backed intensive augment discrepancy

The proposed executable condition is:

```python
code in {'01.0504', '06.0055', '06.0056', '06.0057', '08.0006', '08.0007'} \
    and operations[:1] in [['yaN'], ['yaNluk']] \
    and '7.4.85' in trace_rule_ids
```

An input-only scan of every installed dictionary entry found seven bases containing short vocalic ṛ and ending in a nasal. Six consonant-initial entries generate intensive forms with the suspect nasal augment. The seventh, vowel-initial 08.0005 ṛṇu, generates no intensive control and is preserved. This is an explicit six-code inventory, not a blanket exclusion of a class, nasal-final roots, or ṛ-bearing roots.

| Installed code | Citation | Basis for disposition |
|---|---|---|
| 01.0504 | घृणिँ, Bhvādi | Dhātupradīpa directly prints जरीघृण्ण्यते. The additional nasal makes the derived base non-ṛ-upadha, but the explicit ṛ-bearing extension of 7.4.90 covers it. |
| 06.0055 | पृणँ, Tudādi | Explicit ṛ-upadha rule inference; a separate printed complete paradigm was not required or claimed. |
| 06.0056 | वृणँ, Tudādi | Same explicit rule inference. |
| 06.0057 | मृणँ, Tudādi | Same explicit rule inference. |
| 08.0006 | तृणुँ, Tanādi | Dhātupradīpa directly prints तरीतृण्यते. |
| 08.0007 | घृणुँ, Tanādi | Dhātupradīpa directly prints जरीघृण्यते. |

The source scans are [Dhātupradīpa reader page46, printed36](https://jainqq.org/explore/004319/46) and [reader page132, printed122](https://jainqq.org/explore/004319/132). Both local images were visually inspected; OCR alone was insufficient. [Kāśikā and Nyāsa on 7.4.90](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.90.htm) state the intensive rī augment and its extension to ṛ-bearing bases. [7.4.85](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.85.htm) supplies the ordinary nasal-augment rule and controls such as tan/gam/yam/ram. The printed lexical controls resolve the overlap for this inventory.

VP instead produces, for example, `jaMGfRyate/jaNGfRyate` for 08.0007 and `taMtfRyate/tantfRyate` for 08.0006. The same inner discrepancy propagates into yaN→Ric and yaNluk→Ric. This warrants holding the uncertified branch; this review does **not** assign a guessed replacement gold list for the nested or finite paradigms. Optional r/rī/ri outcomes in intensive-luk would require complete regeneration and source certification before replacement.

[The controls](rnasal-controls.json) contain 84 complete fresh VP derivations: all six suspect entries and six lexical negative controls, each with ordinary, san, Ric, yaN, yaNluk, yaN→Ric, and yaNluk→Ric recipes at Lat/Kartari/Prathama/Eka. All 24 suspect intensive recipe controls satisfy the predicate; all ordinary/san/Ric controls are preserved. The negative controls include vowel-initial ṛṇu, tan, gam, vaṇa, ghṛṣ, and tṛnh. The latter two retain valid ṛ augmentation and do not take the suspect nasal branch.

The full07 panel contains **74 other trace7.4.85 questions: 64 correct and 10 wrong**, all preserved. This guards against excluding every nasal augment or every observed failure. All 12 affected full07 questions were wrong (ghṛṇu8, mṛṇa4). Across earlier named development panels, the proposal also affects only wrong outcomes: Opus01:1; Astra01 pair:1; Opus02:1; Opus03:2; Opus04:4; Astra04 pair:4; Opus05:2; Opus06:4; Astra60 cap diagnostic:1. Every 4D panel has zero affected questions. Counts and IDs, including zero affected successes, are recorded in [the proposal](rnasal-hold-proposal.json).

Candidate04 has **27 affected input questions across four other lexical entries**: 01.0504:7, 06.0055:6, 06.0056:6, 08.0006:8. These are input-only counts. No candidate outcome was accessed. The source-defined predicate therefore extends consistently beyond the development families where the discrepancy was first noticed.

## Nonusable responses

[All 19 records](nonusable.json) have been inspected and retained:

- **16 refusals:** provider `stop_reason=refusal`; visible output is blank, with no explanatory refusal text. Five are all five sampled Lun questions for the single `Self` lexical family. This clustering is relevant to missing-answer bias, but does not establish an invalid input or a particular safety-classification cause. In particular, the earlier campaign's explicit cyber-refusal explanations cannot be attributed to these blank outputs.
- **2 truncations:** 04.0020 ṣṭīma and 01.0808 hrasa reach the 16,384 output cap with thinking and no final answer. These remain incomplete; no retry or replacement is proposed.
- **1 unparsed completed response:** 05.0018 rādh produces three answer tags with conflicting forms and malformed final spelling. The stored parsing failure remains; no preferred tag is salvaged.

Same-family controls and exact response metadata are saved for every item. None is removed by the proposed source hold. All 19 continue to widen the reported missing-response bounds.

## Systematic disagreement checks

A deliberately simple string screen finds **324/527 usable wrong answers** where deleting a short segment near the beginning yields an accepted gold form; 322 remain after the proposed hold. It is only a descriptive screen, not an exhaustive linguistic classification. Typical examples are `acacAkladaH` versus `acAkladaH` and `aciceklindat` versus `aceklindat`.

These examples agree with the already reviewed repeated-reduplication failure: [Kāśikā on 6.1.11](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.1.11.htm) retains the *anabhyāsa* condition. The source does not call for adding another CaN reduplication to an already reduplicated intensive base. This review found no new source reason to quarantine the whole aorist cell.

Additional bounded controls were consistent with keeping the existing scope:

- 01.0105 ṣvaṣka has one correct and three wrong answers; dentalization in the wrong answers conflicts with the explicit ṣvaṣk exception in [Kāśikā 6.1.64](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.1.64.htm). This is distinct from the already held 01.0114 ṣvakka engine bug.
- 04.0020 ṣṭīma has one correct present, four wrong aorists retaining long ī, and one truncated aorist. [7.4.1](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.1.htm) supplies the CaN upadhā shortening control; no independent contradictory source was found.
- 06.0077 tṛnh has two correct, one wrong and one refused result. It is a useful negative control: 7.4.90's ṛ-bearing extension is broader than a literal penultimate-ṛ test, while this entry does not use the suspect nasal-final branch.

Transliterating every usable wrong answer back to SLP1 found **zero exact matches to the stored accepted SLP1 union**. This excludes a simple cross-script equality failure for this panel; it does not certify every possible orthographic alias or every grammar derivation.

The remaining disagreements are not all individually source-certified. This was a bounded validity triage, not exhaustive grammatical proof. No answer-level failures were used to select future questions. The only new hold proposed by this review is the six-code source-backed intensive-augment condition above.

## Reproducibility

[review.json](review.json) records raw input hashes, source links, local scan hashes and the policy18 adapter snapshot. [pattern-groups.json](pattern-groups.json) preserves all-outcome family controls and the mechanical screen. The isolated generator is `misc/vp_4d_pilot07_review.py`; it writes only this review directory. The frozen task files, generation-time hashes, raw responses, shared analyzer and policies were not rewritten.

The isolated producer asserts the original policy18 eligibility context. It intentionally stops if rerun against an adapter that changes that baseline; policy19 now does so. Saved baseline outputs and raw hashes remain available without replaying or rewriting the original comparison.
