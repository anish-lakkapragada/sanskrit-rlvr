# Independent direct-result review

Reviewed 2026-10-07, approximately 22:26 UTC. **The 200/200 modification result survives independent request inspection and regrading; I found no hidden-root/gold leak, response-reuse error or accidental grading success.** Its matched ordinary-4D control result is 197/200. Both arms have 200 completed responses, zero truncations and zero refusals.

This review reads only the completed direct runs selected by `acceleration/plan.json`: `opus-fast-modification-01` through `-05` and `opus-fast-control-01` through `-05`, each containing 40 questions. Original asynchronous batches remain separate. No raw inputs, responses, shared code, scorer or ledger were modified. Reproducible additive checks and fingerprints are in `direct-result-audit.py` and `direct-result-audit.json`.

## Count and request proofs

- The five input slices in each arm exactly concatenate to the original frozen 200-question panel. Slice hashes match the acceleration plan. Every task, result row, custom ID and retained request matches its original position; no duplicate task IDs occur within an arm.
- All 200 modification prompts can be rendered from **only** `source_form_devanagari`, `source_morphology` and `target_morphology`. That rendering exactly matches the single user message in every saved provider request. There are no system messages, prior assistant messages, attachments, active tools or additional task-specific metadata. Root identity and gold remain in local result/audit records, outside the SDK parameters. The direct runner calls the SDK with the saved `params` only; every persisted request-intent digest matches.
- All 400 requests use the same model, xhigh effort and 65,536-token ceiling. Each has a distinct provider message ID. The stored HTTP-200 body, per-request raw result and assembled result agree exactly. I extracted only final text blocks, excluding thinking summaries, and confirmed `end_turn` for all 400.
- Regrading from actual returned text reproduces 200 and 197 successes. A second independent strict regex/NFC membership check also reproduces every score. All 400 responses consist of exactly one `<answer>…</answer>` block, without conflicting multiple answers or surrounding prose. No scoring edge case is needed to obtain these counts.
- All 200 pairs have identical complete SLP1/Devanagari target unions, underlying target coordinates and private verb entry. Control gold was independently regenerated. Full modification validation, including source regeneration and the saved dictionary inverse/collision rules, was rerun for all 200. The source surface is absent from the target gold union in every pair.

Paired transitions are 197 both-correct, three modification-only correct, zero control-only correct and zero both-wrong.

## The three control misses

All three pairs are outside the known held entry. Person, number and Kartari remain fixed; only tense changes.

| Verb code | Given source and tense | Target tense | Control answer | Modification answer / accepted form |
|---|---|---|---|---|
| 10.0461, vawa/Curadi (SLP1) | अववटतम्, Lun | Lrn | अववटतम् | अवटयिष्यतम् |
| 10.0393, SvaWa/Curadi (SLP1) | श्वठयाञ्चकर्थ, Lit | Lan | अश्वाठयः | अश्वठयः |
| 01.0041, Scut/Bhvadi | अश्चोताव, Lan | AshirLin | श्चुन्त्यास्व | श्चुत्यास्व |

The first control supplies an aorist rather than the requested conditional; its coincidence with the modification source is not evidence of cross-request access, since its independently checked request contains only the ordinary target task. The second lengthens the short adanta vowel, whereas the source visibly preserves the short stem. The third adds a nasal absent from the accepted target; the source also displays a nonnasal stem. These are concrete differences from the full keys, rather than tag-format failures. The adanta source mechanism was previously reviewed in `four_d-90/review-mod-agent.md`; this quick review does not newly certify every grammatical form.

## Preserved source sensitivity and interpretation

The pre-outcome hold on Curadi **10.0400** concerns the unresolved complete variant union for competing lexical/derivational analyses. Both arms answered within the frozen union: modification **पतयितास्वहे**, control **पतयितास्वः**. Preserve the raw 200 denominator and report the already declared symmetric sensitivity separately: **199/199 modification versus 196/199 control**. Successful predictions do not resolve that source uncertainty.

The result supports a narrow conclusion: this source-word modification pilot is easy for the tested reference. A source word supplies stem/vowel and inflectional clues while removing the explicit citation. The intervention therefore exchanges information; it is not simply withholding the dhatu from an otherwise identical question. The three gains are consistent with useful source clues, but do not establish the causal mechanism or a reliable superiority: the paired gain is only 1.5 percentage points, with three discordant pairs (two-sided exact McNemar/binomial p = 0.25).

The experiment changes only tense, preserves person/number/voice, covers four source tenses and ten target tenses, and retains only dictionary-scope unambiguous keys. This deliberately removes ambiguity rather than testing unrestricted Sanskrit analysis. Lexical uniqueness is bounded to the audited inventory and licensed ordinary-conjugation domain; the earlier source review documents that limitation. Accepting the full target union also does not require uniquely recovering a hidden pada.

Finally, 200/200 is an observed sample result, not proof of universal accuracy. The reported zero plug-in standard error/degenerate bootstrap at the ceiling should not be treated as certainty; the ordinary iid Wilson 95% interval is approximately 98.12–100%, with additional population-selection limitations. This panel supplies no observed modification errors or evidence of useful below-90% difficulty. It should not be compared causally with the separately concentrated English-prompt 4D panel, and it does not qualify a final benchmark.
