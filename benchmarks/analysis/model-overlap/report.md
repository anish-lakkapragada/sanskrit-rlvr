# Task-level overlap across benchmark runs

All 6,687 task IDs and gold-set scoring verified for seven completed runs.

OpenAI used v1 and Anthropic used v2. All results are single sampled responses; refusals and missing answers count as failures.

## Five distinct models at xHigh

| Number of models correct | Tasks | Share |
|---:|---:|---:|
| 0 | 68 | 1.02% |
| 1 | 109 | 1.63% |
| 2 | 280 | 4.19% |
| 3 | 925 | 13.83% |
| 4 | 2,154 | 32.21% |
| 5 | 3,151 | 47.12% |

## Complementarity with Opus 5.5 xHigh

| Configuration | Its successes also solved by Opus xHigh | Solves Opus misses | Both miss |
|---|---:|---:|---:|
| Opus 5.5 High | 98.88% | 72 | 134 |
| Fable 5.1 xHigh | 98.57% | 88 | 118 |
| Astra xHigh | 98.12% | 115 | 91 |
| Astra High | 98.38% | 97 | 109 |
| Sol xHigh | 98.36% | 88 | 118 |
| Sonnet 5 xHigh | 98.92% | 40 | 166 |

## Pairwise counts

| A | B | Both correct | Only A | Only B | Both unsuccessful |
|---|---|---:|---:|---:|---:|
| Opus 5.5 xHigh | Opus 5.5 High | 6359 | 122 | 72 | 134 |
| Opus 5.5 xHigh | Fable 5.1 xHigh | 6076 | 405 | 88 | 118 |
| Opus 5.5 xHigh | Astra xHigh | 5998 | 483 | 115 | 91 |
| Opus 5.5 xHigh | Astra High | 5884 | 597 | 97 | 109 |
| Opus 5.5 xHigh | Sol xHigh | 5268 | 1213 | 88 | 118 |
| Opus 5.5 xHigh | Sonnet 5 xHigh | 3661 | 2820 | 40 | 166 |
| Opus 5.5 High | Fable 5.1 xHigh | 6045 | 386 | 119 | 137 |
| Opus 5.5 High | Astra xHigh | 5960 | 471 | 153 | 103 |
| Opus 5.5 High | Astra High | 5844 | 587 | 137 | 119 |
| Opus 5.5 High | Sol xHigh | 5257 | 1174 | 99 | 157 |
| Opus 5.5 High | Sonnet 5 xHigh | 3641 | 2790 | 60 | 196 |
| Fable 5.1 xHigh | Astra xHigh | 5785 | 379 | 328 | 195 |
| Fable 5.1 xHigh | Astra High | 5672 | 492 | 309 | 214 |
| Fable 5.1 xHigh | Sol xHigh | 5142 | 1022 | 214 | 309 |
| Fable 5.1 xHigh | Sonnet 5 xHigh | 3598 | 2566 | 103 | 420 |
| Astra xHigh | Astra High | 5755 | 358 | 226 | 348 |
| Astra xHigh | Sol xHigh | 5088 | 1025 | 268 | 306 |
| Astra xHigh | Sonnet 5 xHigh | 3501 | 2612 | 200 | 374 |
| Astra High | Sol xHigh | 5026 | 955 | 330 | 376 |
| Astra High | Sonnet 5 xHigh | 3458 | 2523 | 243 | 463 |
| Sol xHigh | Sonnet 5 xHigh | 3372 | 1984 | 329 | 1002 |

## lakara

| Category | Tasks | Opus 5.5 xHigh | Fable 5.1 xHigh | Astra xHigh | Sol xHigh | Sonnet 5 xHigh |
|---|---:|---:|---:|---:|---:|---:|
| AshirLin | 647 | 96.29% | 90.26% | 94.44% | 79.44% | 42.97% |
| Lan | 633 | 98.42% | 94.31% | 93.36% | 82.62% | 61.45% |
| Lat | 646 | 97.83% | 94.58% | 91.80% | 81.58% | 65.17% |
| Lit | 685 | 95.77% | 87.59% | 89.20% | 80.44% | 48.32% |
| Lot | 629 | 97.77% | 95.39% | 93.48% | 82.67% | 60.57% |
| Lrn | 689 | 97.24% | 93.18% | 91.15% | 83.60% | 56.31% |
| Lrt | 681 | 98.24% | 91.04% | 90.01% | 81.50% | 62.70% |
| Lun | 659 | 91.20% | 87.71% | 83.61% | 61.46% | 29.89% |
| Lut | 712 | 98.74% | 94.10% | 94.94% | 84.41% | 57.02% |
| VidhiLin | 706 | 97.59% | 93.77% | 92.21% | 82.72% | 68.41% |

## prayoga

| Category | Tasks | Opus 5.5 xHigh | Fable 5.1 xHigh | Astra xHigh | Sol xHigh | Sonnet 5 xHigh |
|---|---:|---:|---:|---:|---:|---:|
| Bhave | 2211 | 95.93% | 92.27% | 86.21% | 78.11% | 55.81% |
| Karmani | 2243 | 97.24% | 93.31% | 96.70% | 83.91% | 59.47% |
| Kartari | 2233 | 97.58% | 90.95% | 91.27% | 78.24% | 50.74% |

The CSV contains every task's correctness for every configuration. The JSON includes pairwise metrics, all-seven overlap, five-xHigh overlap, grammatical breakdowns, and source metadata. The task example file retains outcomes and gold forms for hard and disagreement cases.

Coverage by any model uses the known gold labels; it does not establish that an ensemble could choose the right answer.
