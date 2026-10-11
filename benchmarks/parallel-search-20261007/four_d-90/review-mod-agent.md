# Independent input and source review

Reviewed 2026-10-07, before inspecting any answers from this panel. This additive note leaves all submitted inputs, source files, manifests, policy and accounting unchanged.

**Disposition: no concrete grammatical or answer-key blocker found in this bounded review. The principal unresolved issue is scalable family diversity, not the existence of the adanta mechanism.** This is not independent certification of every Sanskrit form, and it does not establish a below-90% benchmark.

## Mechanical and source evidence

I independently regenerated all 200 inputs with the current policy21 adapter, checked the complete SLP1 and Devanagari gold lists, validated every task and checked every rendered prompt hash. There were zero current entry/oracle/local-scope violations. All 20 manifest dependency hashes matched. The task file remains SHA256 `63b7f801151bc5ea15678519f54a19da37e6940641c0cde1b08104f33ab2906c`. I reran all 48 source controls, treating each expected list as a subset of the full engine union; all passed. The previously identified vowel + r + C spelling-coverage concern occurs in none of these 200 gold sets.

The public shape is the ordinary dictionary verb entry and exactly lakara, prayoga, purusha and vacana. No prefix, ordered derivation recipe or separately chosen pada is introduced. All tasks are Kartari. This does not exclude intransitive entries from ordinary active conjugation. There are 118 tasks with multiple accepted forms; the saved key retains the entire engine union. Unspecified pada is therefore handled as an accepted union rather than an undisclosed choice. Regeneration proves preservation of that union, not its grammatical exhaustiveness.

The central source mechanism is supported explicitly: Balamanorama under 6.4.48 explains kathayati and suppression of upadha vrddhi through the retained effect of deleted final a; its 7.4.2 discussion explains that the Curadi adanta final a is part of the entry, not an indicatory or pronunciation-only sound. Consequently these entries cannot simply be treated like superficially similar consonant-final roots. Sources independently read: [6.4.48 commentary](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.48.htm) and [7.4.2 commentary](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.2.htm). The latter also explains the aglopin limitation on aorist shortening; [7.4.93](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.93.htm) states the corresponding restriction on san-like reduplicative behavior. These general conditions support the probe; they do not substitute for checking every lexical exception or every optional branch.

The saved controls appropriately distinguish printed examples from general-rule inference. The uncertain suca aorist is excluded. The generator preserves these local exclusions and current shared scope, and allocates by input predicates and seeded ranks. A representative present/aorist control is not proof that all non-aorist perfect/future/benedictive paradigms are independently certified. Any subsequent disagreement audit must inspect matched successes too and preserve raw results.

## What can scale, and what cannot

The panel has 109 families: 13 short-adanta families contribute eight questions each, and 96 other families contribute one each. Thus 52% of questions come from just 13 families; 60% are Curadi, despite representation of all ten classes and ten tenses. The broad control selection is a seeded finite candidate catalog, not a claim of uniform sampling from every classical dictionary tuple.

The frozen plan records only 14 test families and nine RL families in the short-adanta predicate, plus 25 test families in the other-adanta aorist cell. Those are decisive limitations for the proposed mixture:

| Fixed total | Short-adanta questions at 52% | Average per 14 test families | Minimum repeated family–tense instances beyond one per non-Lun tense |
|---|---:|---:|---:|
| 500 | 260 | 18.6 | 134 |
| 1,000 | 520 | 37.1 | 394 |

There are nine non-Lun tenses. Keeping the pilot's distinct-tense-per-family property allows at most 14 × 9 = 126 questions in the dominant cell, limiting the unchanged 52% mixture to about 242 total questions. Reaching 500–1,000 therefore requires substantial repetition within family and tense using different person/number coordinates. A combinatorial upper bound of 14 × 9 tenses × 9 person/number settings = 1,134 short-cell tuples shows numerical room, but does not certify that all survive source, gold, freshness and surface-duplicate checks.

The other-adanta aorist cell also repeats families when expanded: 8% of N1,000 means 80 tasks across at most 25 test families, averaging 3.2 each in the same tense. Even if every broad-control task gets a different family, the unchanged mixture has upper bounds of 239 distinct families at N500 and 439 at N1,000. These are arithmetic bounds, not regenerated final allocation witnesses.

At 90% accuracy, even independent-item standard error is about 1.34 percentage points for N500 and 0.95 for N1,000. The latter leaves little margin for family dependence; these 14 heavily weighted test families cannot support a sub-1pp claim merely by adding conjugations. The difficulty mechanism may transfer across tenses, but within-root transfer is not new lexical coverage. The nine-family RL supply also limits assessment of broad lexical generalization.

## Interpretation and next decision

A source-clean below-90% outcome could justify this as a concentrated ordinary-4D diagnostic. It would not by itself justify a diverse 500–1,000-question final benchmark under the same proportions. That would require an explicit allocation with repeated-tense counts, family-aware uncertainty, source review and genuinely separate evaluation membership, or a broader grammatical mixture supported by fresh development evidence.

The historical 87.49% forecast is conditional on small development cells, including transport from a 16k ceiling to this 64k ceiling; it is not a prior measurement of this panel. The submitted ordinary-4D panel uses English v1 instructions, whereas the modification experiment's matched 4D controls use Sanskrit v3. Therefore compare modification directly against its own identical-target controls, not against this separate 200-question panel as though language and composition were matched.

No new exclusion, gold correction or global validity claim is proposed. No model outputs were read for this review.
