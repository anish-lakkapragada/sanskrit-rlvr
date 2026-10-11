# Independent full-panel Astra/Opus review

Completed 2026-10-08 UTC (2026-10-07 Pacific). **Reviewed canonical scores remain Astra 161/200 (80.5%) and Opus 175/200 (87.5%).** No concrete key defect, rejected licensed submitted variant, or parsing correction was identified in this bounded review. No new source hold is requested. Both models supplied 200 usable answers, without refusals, truncations or unparsed answers.

The reviewer waited until **all 20 Astra jobs were settled and collected**, first observed at 00:08:48 UTC. PID 22971 remained live while the panel was incomplete and had exited after completion. No interim answers or scores were opened; no process was restarted.

| Predeclared cell | Astra | Opus |
|---|---:|---:|
| Short adanta Curadi, outside Lun | 75/104 — 72.12% | 84/104 — 80.77% |
| Other audited adanta Curadi, Lun | 11/16 — 68.75% | 12/16 — 75.00% |
| Broad coverage outside Curadi | 75/80 — 93.75% | 79/80 — 98.75% |
| Entire identical panel | **161/200 — 80.50%** | **175/200 — 87.50%** |

All 200 Astra requests used gpt-6-astra, standard reasoning with xhigh effort, a 65,536-output-token ceiling, no tools and the unchanged exact4D prompt. Every effective SDK request differs from its registered request only by the declared default service tier. All raw terminal receipts, usage bounds, response identities and extracted final texts were checked. The 200 paired Opus requests contain the identical tasks and prompt text, xhigh effort and the same token ceiling. All **400 canonical grades** were independently reproduced; all **200 complete oracle answer unions** were regenerated. The JSON records all 25 result-file hashes and individual request checks.

## What the 39 Astra misses show

Each miss has an individual JSON record containing its answer, full canonical union, paired Opus answer, source assessment, evidence strength and matched Astra success. Earlier valid source findings were reused where the same issue recurred.

- **21 misses strengthen an adanta stem incorrectly**, including पष→पाषय-, वस→वासय-, श्वठ→श्वाठय-, and कुण→कोणय-. The lexical final-a reading and its deletion do not license the usual strengthening applied to other roots. [6.4.48](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.48.htm).
- **Three misses change कृप दौर्बल्ये to कर्पय- or कल्पय-.** The printed lexical source explicitly gives कृपयति. This repeats the previously reviewed stem-identity issue.
- **Seven misses select the wrong intrinsic ending set:** five on गृह, one on शूर, and one on सत्र. Three गृह answers also substitute गर्हय-. The newly cached and visually inspected [1938 Siddhāntakaumudī, printed page 237](https://jainqq.org/explore/002377/241), explicitly labels the section from पद through गर्व as Atmanepada and includes all three roots. It directly gives गृहयते and the relevant सत्र stem. This restriction belongs to the supplied dictionary entry; it is not an extra coordinate. Requested finite forms use the corresponding grammatical endings.
- **Three adanta aorist misses reverse vowel quantities**, on शील, भाज and वास. Their literal-a reading affects the ordinary shortening/lengthening conditions. The primary lexical identity is explicit; exact finite forms are rule inferences. [7.4.2](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.2.htm), [7.4.93](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.93.htm).

The remaining **five misses outside Curadi** were checked individually:

| Root / requested form | Submitted | Canonical | Assessment |
|---|---|---|---|
| कुर्, Tudadi, AshirLin first dual | कुर्यास्व | कूर्यास्व | Same case as the prior Opus review: required lengthening; the कृ-derived exception is a different lexical case. [8.2.77](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.2.77.htm), [8.2.79](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.2.79.htm). |
| विल्, Tudadi, Lut second dual | विलितास्थः | वेलितास्थः | Missing eligible light-penultimate guṇa. [7.3.86](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.3.86.htm). |
| दमु, Divadi, Lun third plural | अदमिषुः | अदमन् | The relevant Divadi group takes अङ्. Dhatupradipa gives representative अदमत्; the plural is a rule extension. [3.1.55](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.55.htm), [lexical commentary](https://jainqq.org/explore/004319/108). |
| गुड्, Tudadi, Lun second plural | अगोडिष्ट | अगुडिष्ट | Kutadi behavior blocks guṇa; the lexical commentary preserves the short stem. [1.2.1](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/1/1.2.1.htm), [1.1.5](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/1/1.1.5.htm), [lexical commentary](https://jainqq.org/explore/004319/121). |
| मीङ्, Divadi, VidhiLin third dual | मीयेताम् | मीयेयाताम् | Intrinsically Atmanepada; the ya theme combines with the middle optative dual sequence. The commentary explicitly illustrates parallel -ेयाताम् endings. [3.4.102](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.4.102.htm), [1.3.12](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/1/1.3.12.htm). |

These categories total 39 without double counting. Astra's errors span 19 families; **32 of 39 are outside Lun**. Opus's errors span 13 families; **21 of 25 are outside Lun**. The weakness is chiefly non-aorist stem and lexical behavior.

## Paired comparison and spelling sensitivity

There are **144 questions both models answer correctly, 31 correct only for Opus, 17 correct only for Astra, and eight wrong for both**. Astra is seven percentage points lower on this panel. A separate family bootstrap gives an approximate 95% interval of **−16.13 to +1.68 percentage points** for Astra minus Opus (20,000 resamples, seed 20261008). The exact discordant-pair binomial comparison gives p≈0.0595 under its question-level assumptions. Neither calculation establishes a definitive population ranking from this adaptive, family-dependent pilot.

The existing finite spelling rules were applied **symmetrically as a post-result sensitivity audit** to all 200 questions for both models. They rescue **zero** submitted responses on either side. This does not retroactively replace the frozen canonical scoring policy. The prior 25-miss Opus source review and all five result-file hashes remain unchanged.

## Limits and practical implication

This supports a below-90% development signal on both tested models under this protocol. Opus remains the stronger observed model at 87.5%. It motivates a prospectively frozen held-out test of the grammar-defined mixture; it does **not** establish the unscored 1,250-question candidate's accuracy.

The review does not claim exhaustive licensed-spelling coverage or independently printed full paradigms. Lexical witnesses and representative forms often require extension by grammatical rules. Any later established source correction must be applied symmetrically while preserving these raw scores. The panel has only 13 heavily weighted short-adanta families; neither this pilot nor a larger task count alone establishes family-generalization uncertainty below one percentage point.

No provider calls, ledger/job edits, task changes or raw-result changes were made. The machine audit is independent-result-review.json; independent-result-review.py reproduces the mechanical checks. This review does not mark the benchmark final or ready.
