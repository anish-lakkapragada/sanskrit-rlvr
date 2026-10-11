# 4D pilot 02: licensed endings and cross-class lexical identity

**108 fresh development questions are frozen**, spanning 82 families, all ten ganas and lakaras, and exactly 36 questions per person and number. The questions ask for one form from exactly dictionary dhatu + lakara/prayoga/purusha/vacana. The existing renderer is unchanged. No paid call was made by this worker.

Question SHA256: `9a0de5f7b3a98e8a06bef47b9ec07d49e18f51af5edd2ccdeaa877cb6792074e`. Request: `experiment-request-02.json`.

## Prespecified design

| Cell | Questions | Families | Purpose |
|---|---:|---:|---|
| Licensed Akusmiya | 36 | 10 | Test lexical Atmanepada restrictions across all ten lakaras |
| Cross-gana lexical contrast | 36 | 36 | Test class-specific present-system formation for citations occurring in multiple ganas |
| Coordinate-matched controls | 36 | 36 | Match the full morphology-count distribution of Akusmiya; 18 ordinary Curadi and two roots from every other gana |

The class-contrast cell contains nine Bhvadi, seven Tudadi, seven Divadi, five Kryadi, three Svadi, two Rudhadi, two Juhotyadi and one Adadi questions, with nine each in Lat, Lan, Lot and VidhiLin. Its predicate is defined entirely by dictionary metadata: remove accent signs only for pool membership, then require the remaining exact citation to occur in at least two ganas. Full citations, including accents and it-markers, remain in the prompt. The selected roots are non-Curadi. No answers or comparative gold forms determine predicate membership.

The seed is 2026100702. Integer selection applies fixed grammatical quotas and a seeded priority, with no model correctness input. All 108 tasks are fresh relative to original tasks, discovery panels, prior pure-4D evaluation tasks, and pilot01. The 36 Akusmiya tasks use at most four per family; the other cells use one per family, with no family reused between cells. Each control set is matched in aggregate by all four morphology coordinates; it is not a randomized causal experiment or a frequency-matched lexical sample.

All tasks use Kartari to isolate the proposed mechanisms. Curadi is 54/108 (50%), and the largest lakara count is 17/108. This is an exploratory mechanism panel, not a proposed final release composition; the earlier release diversity constraints are unchanged.

## Source and oracle audit

The lexical audit precedes sampling. The [Dhatupatha](https://sa.wikisource.org/wiki/अष्टाध्यायी-धातुपाठः) and [Dhatupradipa](https://jainqq.org/booktext/Dhatupradip/004319) identify the Akusmiya subgroup and supply individual readings/examples. Four unverified dictionary readings are excluded throughout: 10.0205 kila, 10.0206 pila, 10.0222 kuwa in the cutting sense, and 10.0226 kuwwa in the heating sense. The inspected editions do not establish those exact entries; absence is not proof they are ungrammatical. Four other development roots with optional no-Nic branches are kept out of the focused cell, preserving its intended ending mechanism.

The frozen focused cell uses qipa, tarja, bhartsa, bhruna, shatha, kutsa, truta, gala, mana and yu. Nine have direct present-form examples in the inspected source; gala has a direct lexical entry and a rule-derived form under [3.1.25](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.25.htm) and [7.2.116](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.2.116.htm). The JSON preserves exact SLP1 citations and evidence levels. Grammatical variants are never narrowed to force an ending choice.

The audit passes 31 source/rule controls: 30 direct forms and one rule-derived form, including a complete ten-lakara third-singular Divadi example. Class-specific controls come from primary commentaries on 3.1.25, 3.1.69, 3.1.73, 3.1.79, 2.4.72 and 2.4.75. These are representative controls, not an assertion that every generated paradigm has independent certification.

All 108 tasks pass the hardened shared validator, complete VP regeneration, transliteration checks, and unique-prompt/visible-tuple checks. The generator rejects inherited prefixes/sanadi, ambiguous visible dictionary identities, the semantic 6.4.123 context, the two disputed aorist-list contexts, and other applicable shared oracle quarantines. The family split is unchanged.

## Existing evidence and scaling limits

Pilot01 raw scores remain **108/120 overall and 108/118 usable**. Shared oracle-policy exclusions give 108/116 usable. Applying the four prospective unverified-reading exclusions also removes two misses and one correctly answered passive, giving **107/113 usable**. This is a read-only post-discovery diagnostic, not a new independently measured score. Refusals remain separate in every view. No prior task, raw gold, model response or score was edited.

The remaining six exact-answer misses are five internal vowel-lengthening cases and one Divadi aorist case. At their observed rates, the existing groups do not suggest a reliable 80% release. The following deliberately optimistic plug-in scenarios cap each existing cell at 25%; an additional Akusmiya column assumes every eligible Akusmiya question is wrong. That assumption has no supporting licensed-subgroup measurement yet.

| N | Maximum per family | Old-cell accuracy floor at plug-in rates | Including hypothetical all-wrong Akusmiya |
|---:|---:|---:|---:|
| 1000 | 3 | 96.60% | 91.50% |
| 1601 | 5 | 96.56% | 91.25% |
| 1000 | 6 | 95.48% | 85.28% |
| 1601 | 6 | 96.32% | 89.95% |
| 1000 | 10 | 93.98% | 76.98% |
| 1601 | 10 | 95.39% | 84.77% |

Without a family maximum, the two observed error-bearing old cells at 25% each imply an 87.31% plug-in floor. These are sensitivity scenarios, not statistical lower bounds or a proof of infeasibility: the small pilot rates are uncertain, families and cells overlap, and larger family repetition remains possible. Counts do not certify standard error below one point. Cross-gana homographs can belong to different existing families and splits; the master split is preserved, but a final uncertainty analysis should also cluster by accent-stripped citation across ganas. This stricter related-root grouping may reduce effective family counts.

Unlike the narrow subgroup, the new non-Curadi class-contrast predicate has **6,840 grammar-valid test tuples across 184 families** in the full master test split. Its separate capacity is 552 tasks at three per family, 920 at five, and 1,104 at six, before joint diversity constraints. It adds 115 families to the earlier predicate union. After the newly added lexical-reading exclusions, the combined pool is **17,849 tuples across 578 families**. No final members have been selected, and no test model answers or test gold surfaces were read for this census.

## Analysis plan before pilot02 answers

Report overall and per-cell exact accuracy, usable-answer accuracy, refusals, truncations, and invalid/infrastructure outcomes separately. Report all construction results even if easy. Review every model-oracle disagreement before interpreting a difficulty effect. For Akusmiya, inspect ending selection and class-inherent stem formation separately; an acceptable alternative remains correct. For lexical contrast, classify wrong-gana stems separately from unrelated phonological or ending mistakes. Compare against the matched control cells descriptively; this panel does not identify a causal effect of homography.

A useful broad lead would show at least six source-supported grammatical errors among the 36 class-contrast cases, spread over at least four families and three ganas. This is a pragmatic follow-up trigger, not a significance test or a release acceptance criterion. If that lead has signal, the next Opus sample should add fresh families and preserve fixed class/tense quotas in a larger development panel. The licensed Akusmiya cell can support a limited component but should not dominate spending or the final release through repeated roots.

The coordinator may pair Astra on the same frozen panel if Opus reveals a credible, audited mechanism. Any expanded panel must be selected by declared grammar predicates, not by repeating the failed questions. Final weights, membership, and a family-aware precision/extension rule remain unfrozen until development evidence supports them.

## Artifacts

- `pilot-02.questions.json`, `pilot-02.manifest.json`, `pilot-02.audit.json`
- `pilot-02.lexical-audit.json` and `misc/vp_4d_pilot02_audit.py`
- `pilot-01.clean-context-stats-02.json` (original raw files unchanged)
- `pilot-02.supply-extension.json`, `pilot-02.scaling-scenarios.json`
- `experiment-request-02.json` and `misc/vp_4d_pilot02.py`

Budget estimate: maximum Opus reservation $18.01872 using 1,500 input tokens and 16,384 output tokens per question; the coordinator must recompute it under the existing shared budget lock. Worker spend is zero. Benchmark readiness remains false.
