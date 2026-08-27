| Model | pass@1 [95% CI] | pass@2 | pass@4 | pass@8 | pass@16 | Solved | FLORES-200 chrF/chrF++ (tag%, n) | Samayik chrF/chrF++ (tag%, n) |
|---|---|---|---|---|---|---|---|---|
| Qwen3-4B (base) | 0.03% [0.00, 0.07] | 0.06% | 0.11% | 0.22% | 0.45% | 3/669 | 21.19/17.21 (90.0%, 1808) | 15.18/12.23 (94.1%, 706) |
| 10M · 100% samayik | 0.00% [0.00, 0.00] | 0.00% | 0.00% | 0.00% | 0.00% | 0/669 | 24.47/19.79 (86.5%, 1737) | 41.81/38.33 (96.3%, 722) |
| 10M · 67% samayik | 26.52% [24.48, 28.61] | 39.58% | 53.12% | 65.10% | 74.59% | 499/669 | 23.24/18.88 (74.9%, 1504) | 40.15/36.59 (96.3%, 722) |
| 10M · 50% samayik | 35.65% [33.42, 37.96] | 50.75% | 64.27% | 74.55% | 81.61% | 546/669 | 22.58/18.31 (78.8%, 1584) | 38.09/34.70 (93.1%, 698) |
| 10M · 33% samayik | 42.02% [39.56, 44.52] | 56.81% | 68.54% | 76.17% | 80.87% | 541/669 | 23.20/18.69 (76.3%, 1533) | 37.10/33.28 (93.3%, 700) |
| 10M · 0% samayik | 50.54% [48.00, 53.06] | 65.36% | 76.09% | 82.66% | 86.40% | 578/669 | 9.83/7.77 (71.3%, 1433) | 8.36/6.58 (82.1%, 616) |
| 15M · 100% samayik | 0.00% [0.00, 0.00] | 0.00% | 0.00% | 0.00% | 0.00% | 0/669 | 23.52/19.06 (95.3%, 1915) | 42.58/39.09 (99.9%, 749) |
| 15M · 67% samayik | 37.24% [34.70, 39.82] | 50.08% | 60.85% | 69.32% | 75.78% | 507/669 | 25.50/20.65 (89.4%, 1796) | 40.99/37.10 (97.3%, 730) |
| 15M · 50% samayik | 44.73% [42.26, 47.28] | 59.41% | 70.64% | 78.10% | 83.41% | 558/669 | 23.91/19.46 (89.1%, 1790) | 40.33/36.87 (97.3%, 730) |
| 15M · 33% samayik | 53.71% [51.02, 56.39] | 67.22% | 76.49% | 82.74% | 87.44% | 585/669 | 23.86/19.25 (80.5%, 1618) | 38.83/34.96 (93.1%, 698) |
| 15M · 0% samayik | 56.59% [54.00, 59.23] | 70.27% | 79.24% | 84.96% | 89.09% | 596/669 | 9.91/7.72 (81.7%, 1641) | 8.48/6.62 (85.9%, 644) |
| 20M · 100% samayik | 0.00% [0.00, 0.00] | 0.00% | 0.00% | 0.00% | 0.00% | 0/669 | 24.19/19.61 (96.9%, 1947) | 43.86/40.21 (99.3%, 745) |
| 20M · 67% samayik | 46.15% [43.59, 48.70] | 60.77% | 71.82% | 79.34% | 84.75% | 567/669 | 22.97/18.64 (90.4%, 1817) | 41.29/37.80 (97.9%, 734) |
| 20M · 50% samayik | 47.71% [45.20, 50.29] | 62.67% | 74.43% | 82.23% | 87.29% | 584/669 | 23.56/19.20 (83.8%, 1683) | 40.04/36.56 (95.6%, 717) |
| 20M · 33% samayik | 54.56% [52.00, 57.12] | 69.11% | 78.97% | 85.14% | 88.94% | 595/669 | 23.55/19.14 (83.6%, 1679) | 39.70/36.31 (96.7%, 725) |
| 20M · 0% samayik | 61.31% [58.69, 63.89] | 74.10% | 81.52% | 85.52% | 88.04% | 589/669 | 6.45/5.05 (44.1%, 886) | 6.13/4.84 (63.2%, 474) |

## GRPO round 3 (vp_exact, one epoch on 5,844 prompts, from 20M · 67% samayik)
| Model | pass@1 [95% CI] | pass@2 | pass@4 | pass@8 | pass@16 | Solved | FLORES-200 chrF/chrF++ (tag%, n) | Samayik chrF/chrF++ (tag%, n) |
|---|---|---|---|---|---|---|---|---|
| GRPO-r3 final (step 731) | 62.45% [59.69, 65.19] | 73.45% | 79.96% | 84.28% | 87.89% | 588/669 | 22.78/18.47 (89.3%, 1795) | 41.27/37.73 (98.8%, 741) |
| GRPO-r3 ckpt-378 | 58.49% [55.77, 61.29] | 70.49% | 77.99% | 82.59% | 85.65% | 573/669 | 22.84/18.50 (90.4%, 1817) | 41.60/38.09 (98.0%, 735) |

## Addendum (2026-08-27): GEMBA LLM-judge metrics — DA_ref + MQM, all 17 models

**Why.** chrF structurally cannot price grammar: the answer-key ceiling experiment
(misc/answer-key-ceiling/) showed a translation perfect except for every verb inflection
still scores ~93 chrF, so verb-morphology transfer was sub-noise in the columns above *by
construction*. GEMBA-MQM is a grammar-sensitive instrument (per-error-category counts), so
it re-tests the transfer question with real headroom (~30–50 grammar errors per 100
segments at the operating point). Precedent: Mitrasamgraha (arXiv:2601.07314) finds GEMBA
variants beat BLEU/chrF against Sanskrit-PhD human rankings.

**Protocol.** Judge = claude-opus-5 (Batch API, thinking disabled; Claude 5 rejects the
`temperature` param, so model-default sampling). Templates verbatim from
MicrosoftTranslator/GEMBA: GEMBA-DA_ref (reference-based scalar 0–100) and GEMBA-MQM
(reference-free 3-shot error-span QE; score = −(25·critical + 5·major + 1·minor), first 5
errors, floor −25; upstream parser port). Scored segments = exactly the tag-conditional
sets of the chrF columns above (same n; the 39 Hindi rows in samayik-eval are included to
keep denominators identical). 80,034 judge calls, ~$287. Harness + raw outputs:
misc/gemba/ (gemba_eval.py, results/raw-*.jsonl, results/summary.json). Error-rate columns
are per 100 segments; a segment can carry multiple errors.

### Samayik — GEMBA (judge: claude-opus-5, thinking disabled)

| Model | GEMBA-DA_ref mean [95% CI] | GEMBA-MQM mean [95% CI] | fluency-grammar /100 | acc-mistranslation /100 | non-translation /100 | n |
|---|---|---|---|---|---|---|
| Qwen3-4B (base) | 24.4 [22.8, 25.9] | -22.59 [-23.01, -22.13] | 49.0 | 81.9 | 68.6 | 706 |
| 10M · 100% samayik | 74.8 [73.4, 76.1] | -9.14 [-9.81, -8.50] | 31.9 | 60.7 | 4.4 | 722 |
| 10M · 67% samayik | 72.2 [70.7, 73.7] | -10.16 [-10.78, -9.51] | 36.3 | 67.7 | 7.3 | 722 |
| 10M · 50% samayik | 69.2 [67.5, 70.9] | -10.98 [-11.62, -10.34] | 37.2 | 68.8 | 6.0 | 698 |
| 10M · 33% samayik | 67.9 [66.3, 69.5] | -11.26 [-11.90, -10.63] | 43.3 | 71.4 | 7.0 | 700 |
| 10M · 0% samayik | 5.9 [5.1, 6.9] | -24.50 [-24.73, -24.25] | 2.6 | 9.6 | 92.4 | 616 |
| 15M · 100% samayik | 74.3 [72.9, 75.8] | -9.40 [-10.03, -8.71] | 33.5 | 60.1 | 5.1 | 749 |
| 15M · 67% samayik | 74.4 [73.2, 75.9] | -9.02 [-9.60, -8.41] | 34.1 | 60.4 | 4.2 | 730 |
| 15M · 50% samayik | 73.2 [71.7, 74.7] | -9.59 [-10.20, -8.97] | 35.3 | 70.0 | 5.9 | 730 |
| 15M · 33% samayik | 68.6 [66.9, 70.4] | -10.92 [-11.66, -10.24] | 37.2 | 71.8 | 7.4 | 698 |
| 15M · 0% samayik | 6.4 [5.6, 7.4] | -24.49 [-24.70, -24.25] | 4.5 | 11.2 | 90.8 | 644 |
| 20M · 100% samayik | 75.6 [74.3, 76.9] | -9.09 [-9.71, -8.50] | 30.2 | 60.8 | 6.0 | 745 |
| 20M · 67% samayik | 73.7 [72.2, 75.1] | -9.49 [-10.12, -8.85] | 32.8 | 57.5 | 6.0 | 734 |
| 20M · 50% samayik | 72.6 [70.9, 74.1] | -9.97 [-10.59, -9.36] | 31.5 | 60.8 | 6.8 | 717 |
| 20M · 33% samayik | 70.9 [69.2, 72.5] | -10.18 [-10.81, -9.49] | 33.0 | 66.9 | 6.9 | 725 |
| 20M · 0% samayik | 5.5 [4.4, 6.7] | -24.30 [-24.60, -23.94] | 3.0 | 4.9 | 90.3 | 474 |
| GRPO-r3 final (step 731) | 74.1 [72.7, 75.4] | -9.76 [-10.41, -9.11] | 31.8 | 60.2 | 6.3 | 741 |

### FLORES-200 — GEMBA (judge: claude-opus-5, thinking disabled)

| Model | GEMBA-DA_ref mean [95% CI] | GEMBA-MQM mean [95% CI] | fluency-grammar /100 | acc-mistranslation /100 | non-translation /100 | n |
|---|---|---|---|---|---|---|
| Qwen3-4B (base) | 19.7 [18.9, 20.4] | -24.61 [-24.71, -24.50] | 46.2 | 111.9 | 91.6 | 1808 |
| 10M · 100% samayik | 53.0 [52.0, 54.1] | -19.91 [-20.25, -19.57] | 49.4 | 150.2 | 17.6 | 1737 |
| 10M · 67% samayik | 48.2 [47.0, 49.3] | -20.79 [-21.13, -20.44] | 50.4 | 141.8 | 23.0 | 1504 |
| 10M · 50% samayik | 45.3 [44.0, 46.6] | -21.21 [-21.52, -20.91] | 58.4 | 138.5 | 29.3 | 1584 |
| 10M · 33% samayik | 47.1 [46.0, 48.3] | -20.91 [-21.23, -20.54] | 62.6 | 140.6 | 25.0 | 1533 |
| 10M · 0% samayik | 4.6 [4.2, 5.0] | -24.98 [-25.00, -24.96] | 1.9 | 6.2 | 102.5 | 1433 |
| 15M · 100% samayik | 52.7 [51.6, 53.7] | -19.79 [-20.11, -19.45] | 45.2 | 141.0 | 18.0 | 1915 |
| 15M · 67% samayik | 56.5 [55.5, 57.4] | -19.37 [-19.72, -19.03] | 53.9 | 150.3 | 16.6 | 1796 |
| 15M · 50% samayik | 50.8 [49.7, 51.9] | -20.53 [-20.83, -20.23] | 54.6 | 150.7 | 21.1 | 1790 |
| 15M · 33% samayik | 47.7 [46.5, 48.9] | -20.94 [-21.27, -20.62] | 60.2 | 140.7 | 27.9 | 1618 |
| 15M · 0% samayik | 4.1 [3.8, 4.4] | -24.97 [-25.00, -24.94] | 1.7 | 5.5 | 101.6 | 1641 |
| 20M · 100% samayik | 53.6 [52.6, 54.5] | -19.98 [-20.27, -19.65] | 50.1 | 148.8 | 17.2 | 1947 |
| 20M · 67% samayik | 49.1 [48.1, 50.3] | -20.02 [-20.34, -19.68] | 45.1 | 134.8 | 20.9 | 1817 |
| 20M · 50% samayik | 50.6 [49.5, 51.8] | -19.92 [-20.26, -19.58] | 44.7 | 140.6 | 18.6 | 1683 |
| 20M · 33% samayik | 49.0 [47.9, 50.2] | -20.53 [-20.88, -20.22] | 50.6 | 136.2 | 24.5 | 1679 |
| 20M · 0% samayik | 2.9 [2.6, 3.4] | -24.95 [-25.00, -24.87] | 0.7 | 3.6 | 101.5 | 886 |
| GRPO-r3 final (step 731) | 48.8 [47.6, 49.9] | -20.16 [-20.45, -19.82] | 44.7 | 132.2 | 21.3 | 1795 |

**Key readings.**
1. **The dissociation survives a grammar-sensitive metric.** SFT-start (20M·67%) → GRPO-r3
   on Samayik: DA 73.7 → 74.1, MQM −9.49 → −9.76, fluency-grammar 32.8 → 31.8 per 100 —
   all within CI. FLORES likewise (DA 49.1 → 48.8, grammar 45.1 → 44.7). +16.3pp of drill
   accuracy produced no measurable grammar improvement inside translation, on an
   instrument with ~33 errors/100 of headroom. The null is real, not chrF blindness.
2. **Sanity anchors passed.** The 0%-samayik arms crater exactly as they must
   (non-translation ≈ 90–103/100, DA ≈ 3–6); 100%-samayik arms lead DA on Samayik.
3. **Grammar-in-translation tracks translation data, not morphology data.** At 10M budget,
   grammar errors rise 31.9 → 43.3 per 100 as the samayik share falls 100% → 33%, while the
   dedicated morphology task soars — drills don't teach grammar-in-use.
4. **Matched-token titration confirms zero exchange rate.** Fixed ~10M samayik tokens with
   +0/+5/+10M drill tokens (10M·100% / 15M·67% / 20M·50%): DA 74.8 / 74.4 / 72.6, grammar
   31.9 / 34.1 / 31.5 — extra drill tokens buy nothing a grammar-sensitive judge can see.
5. FLORES sits near the MQM floor (≈ −20 of −25) for all trained arms; DA_ref is the more
   discriminative metric out-of-domain.

