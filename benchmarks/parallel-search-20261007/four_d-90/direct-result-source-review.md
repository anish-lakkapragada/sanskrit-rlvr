# 4D direct pilot: bounded source and scoring review

2026-10-07, completed after the frozen direct results became available. This is a review of the development pilot, not final benchmark certification.

**The reviewed score remains 175/200 (87.5%).** I inspected all 25 misses, regenerated all 200 tasks and complete accepted-answer sets, and independently repeated answer extraction and scoring. No parsing artifact, observed licensed answer rejected, or concrete invalid gold answer was identified. No score correction or new quarantine is requested. All 200 responses were usable, with no truncation or refusal.

| Predeclared cell | Correct / total | Accuracy | Families with errors |
| --- | ---: | ---: | ---: |
| Short-penultimate adanta Curadi, outside Lun | 84 / 104 | 80.77% | 8 |
| Other audited adanta Curadi, Lun | 12 / 16 | 75.00% | 4 |
| Broad coverage outside Curadi | 79 / 80 | 98.75% | 1 |
| Total | 175 / 200 | 87.50% | 13 |

## What the errors are

**Seventeen misses incorrectly strengthen the stem vowel.** They involve वट, शठ, श्वठ, वस, गृह, and कुण. Examples include वाटयाव instead of वटयाव and गर्हय- instead of गृहय-. These dictionary entries contain a grammatical final, non-nasalized *a*. Its deletion preserves conditions that prevent the usual strengthening. This is supported by the specific lexical entries in the [Siddhantakaumudi](https://sa.wikisource.org/wiki/सिद्धान्तकौमुदी/प्रकरण‌५१-६०) and the explanation of [6.4.48](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.48.htm). Listed alternative lexical analyses of वट do not license the submitted वाटय- stem for the frozen entry.

**Two misses substitute कल्पय- for कृपय-.** The task identifies कृप in the sense of weakness, for which the lexical source gives कृपयति. कल्पयितास्मि and कल्पयेयुः therefore use the wrong stem. This is not a harmless spelling alternative; see the same [lexical source](https://sa.wikisource.org/wiki/सिद्धान्तकौमुदी/प्रकरण‌५१-६०).

**One conditional dual adds a final visarga:** अश्रथयिष्यावः instead of अश्रथयिष्याव. The first-person ending loses its final *s* in this environment; [3.4.99](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.4.99.htm) supports the deletion.

**Two aorist misses reverse vowel quantities:** अशीशिलः versus अशिशीलः, and अचूकुटन् versus अचुकूटन्. For these adanta entries, the model applies the ordinary pattern where final-*a* deletion changes the applicable conditions. The lexical specification together with [7.4.2](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.2.htm) and [7.4.93](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.93.htm) supports the accepted quantities.

**One aorist miss inserts an unsupported vowel:** आर्तिथथाः versus आर्तथथाः. The [Siddhantakaumudi](https://sa.wikisource.org/wiki/सिद्धान्तकौमुदी/प्रकरण‌५१-६०) directly prints the corresponding third-person stem form आर्तथत. Applying the requested ending supports the gold; the exact requested second-person form is a rule-based inference.

**One aorist miss uses dental न् before क:** अससन्केतत versus अससङ्केतत. This differs from the licensed anusvara/homorganic-nasal spelling question: the submitted consonant is dental. Internal nasal changes are supported by [8.3.24](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.3.24.htm) and [8.4.58](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.58.htm).

**The broad-control miss omits required lengthening:** कुर्यास्व versus कूर्यास्व for Tudadi कुर्, “sound.” [8.2.77](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.2.77.htm) supports the long vowel. I checked the superficially relevant exception [8.2.79](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.2.79.htm): its commentary and [Dhatupradipa](https://jainqq.org/booktext/Dhatupradip/004319), printed page 108, entry 60 and note 9, distinguish this lexical root from the कृ-derived form to which that exception applies.

## Verification and limits

All 200 frozen task dictionaries matched regeneration under the existing policy and all 200 scores matched independent extraction and normalization. The review also inspected 25 matched-success comparisons, representing 19 distinct successes, choosing the same family and cell where available. These comparisons help check consistent treatment of accepted variants; they are not another evaluation cohort.

The [machine-readable audit](direct-result-source-review.json) records every miss, submitted and accepted forms, evidence strength, matched-success IDs, all five raw-result hashes, and local source hashes. Frozen task SHA-256: `63b7f801151bc5ea15678519f54a19da37e6940641c0cde1b08104f33ab2906c`. Raw results and tasks were not changed.

The lexical sources often explicitly establish the relevant stem; extending that evidence to a requested person/number/tense uses grammatical rules. This review does **not** independently enumerate every licensed spelling or full paradigm for every task, and reproducing the oracle is not independent proof of its entire answer universe.

The result is a useful below-90% development signal on the tested model. It does not establish strongest-model performance, a final held-out benchmark, or sub-one-percentage-point uncertainty. Diversity remains qualified: the panel has 109 families and all ten classes and tenses, but 60% of questions are Curadi and 52% come from only 13 short-adanta families. Lun is only 12% of the panel, and 21 of the 25 errors are outside Lun. The observed weakness is therefore primarily a non-aorist lexical/stem rule, while the small number of eligible hard families remains the principal scaling limitation.
