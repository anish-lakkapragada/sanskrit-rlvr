# Independent candidate source review

This unpaid review found **four gold-validity blockers affecting seven inputs** in candidate revisions 01 and 02. A separate classical-scope review recommends excluding dictionary codes **02.0071–02.0074** across coordinates and recipes while preserving **02.0075 vaś**. The scope proposal overlaps three of those seven candidate inputs. These are proposals for the coordinator; this review changed no shared policy, candidate, gold, or model result.

The screened candidate is revision 01, SHA-256 `d639305f42598f3eee133865312399832653be98a7737b5f763e77832e4f063a`. The original coordinator screen contains 38 novel trace rules. Sixteen occur in **18 single-san inputs across 12 lexical roots**; the remaining rules occur only in nested intensive/causative recipes, which the coordinator audits separately. All 18 single-san inputs regenerated exactly. Mechanical agreement is not source certification.

## Blockers

| Input predicate | Candidate inputs | Finding |
|---|---:|---|
| 01.0262 aj, exactly `[san]`, Lit/Lut/Lrt/AshirLin/Lun/Lrn | 2 | The engine forms the desiderative, then substitutes aj → vī again. It produces `ajivayiz-` or drops the `ajijiz-` alternative. |
| 02.0071 dīdhī or 02.0072 vevī, exactly `[san]` | 3 | Rule 7.4.53 deletes final ī twice, removing a consonant on the second pass. This affects bare and finite desideratives. |
| 04.0160 ṛdh, exactly `[san]`, Lan/Lun/Lrn | 1 | After inserting the augment, rule 7.4.55 runs again: `Ir` → `IIr` → `AyIr`. Nonaugmented controls preserve the correct stem. |
| 02.0067 jāgṛ, exactly `[san]` | 1 | Rule 7.2.12 incorrectly suppresses iṭ for a nonmonosyllabic root, producing `jijAgIrza` instead of source-supported `jijAgariza`. |

For aj, the directly printed control is **अजिजिषति**; the vī substitution is optional before the relevant consonant-initial suffix. Present-system controls retain both proper stems. The nonpresent forms proposed for comparison are regular inflectional inferences, not new gold. [Bṛhaddhāturūpāvali, aj entry 89](https://sa.wikisource.org/wiki/बृहद्धातुरूपावलिः), [Kāśikā/Nyāsa 2.4.56](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/2/2.4.56.htm).

For dīdhī/vevī, the source specifies deletion of the final ī before y/i, not successive deletion of the new final consonant. Traces show `dIDI → dID → dI` and `vevI → vev → ve`. This defect stands independently of their dialect restriction. [Nyāsa and Bālamanoramā 7.4.53](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.53.htm).

For ṛdh, **ईर्त्सति** and **अर्दिधिषति** are direct primary controls. The candidate contains `AyIrtsizuH`; the comparison `ErtsizuH` is inferred from the documented stem and ordinary augmentation. [Kāśikā 7.4.55](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.55.htm), [Kāśikā 7.2.49](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.2.49.htm).

For jāgṛ, the Mādhavīya commentary explicitly supplies **जिजागरिषति** and explains that the inherited *ekāc* condition prevents 7.2.12 here. Pañcagranthī independently lists that form among seṭ examples. [Mādhavīya Dhātuvṛtti, entry 62, primary-text transcription hosted by Kosha](https://kosha.sanskrit.today/word/sa/जागृ), [Pañcagranthī, printed p.257](https://jainqq.org/explore/004311/331/).

Exact task IDs, source distinctions, proposed predicates, and before/after trace events are in [blockers.json](blockers.json). [lexical-san-controls.json](lexical-san-controls.json) contains complete actual-candidate traces and bare/Lat/Lit/Lrt/Lun controls. [suspect-tense-grid.json](suspect-tense-grid.json) records the ten-tense checks for the first three issues. No blanket exclusion of these rules or all roots bearing their phonology is proposed.

## Classical scope correction

Installed identities are 02.0071 `dIDIN`, 02.0072 `vevIN`, 02.0073 `zasa~`, 02.0074 `zasti~`, and 02.0075 `vaSa~`. The proposed classical hold is **exact codes 71–74 only**, independently of requested recipe.

Direct Mahābhāṣya 1.1.6 identifies dīdhī/vevī as Vedic. Mahābhāṣya 6.1.6 similarly characterizes ṣas/vaś; Bālamanoramā includes ṣasti in the restricted group but explicitly recognizes vaś's classical uses. That supports preserving 75 while excluding 71–74 for this declared classical Pāṇinian benchmark. [Mahābhāṣya 1.1.6](https://www.ashtadhyayi.com/bhashya/4?scroll=bhashya-11009), [Mahābhāṣya 6.1.6](https://ashtadhyayi.com/sutraani/lsk345), [Bālamanoramā/Tattvabodhinī 7.4.53](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.53.htm).

The earlier unresolved classification in `search-03.lexical-scope-scan.json` relied partly on contradictory Kṣīrataraṅgiṇī editorial wording: printed p.168 says *acchandasatva*, while p.167 cites the Bhāṣya for Vedic scope. Direct inspection of the Bhāṣya resolves that contradiction. Kātantra's different treatment is not a license to import another grammatical protocol silently. The historical scan remains unchanged. [Kṣīrataraṅgiṇī, pp.167–168](https://jainqq.org/booktext/Kshir_Tarangini/002433).

[classical-scope-proposal.json](classical-scope-proposal.json) records uniform effects on all existing 4D/5D pilots, the cap diagnostic, and candidate versions. This hold alone would change 4D pilot 01 from 97/100 to **96/99 completed**; other 4D pilots are unaffected. It removes one input each from Opus 5D pilots 01–03, two each from 04–06, and the matching Astra pairs. The cap diagnostic loses zero inputs. Candidate revisions 01 and 02 each lose the three dīdhī/vevī inputs already identified above. Development counterfactuals use existing score fields only, after freezing the source predicate.

## Remaining single-san controls

These seven roots account for the other 11 screened inputs. No additional candidate blocker was found in the named mechanisms; complete rare finite paradigms are not claimed independently printed.

| Root | Source control and inference |
|---|---|
| 01.0511 kam | Intrinsic ṇiṅ and its optional absence in an ārddhadhātuka environment support `cikAmayiz-` / `cikamiz-`; both occur in the actual Lun/Lut inputs. [3.1.30](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.30.htm), [3.1.31](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.31.htm). |
| 01.1102 uṅ | `Uziza-` follows vowel lengthening and reduplication of the following syllable. Hemacandra directly prints **ऊषिषते** as a cross-tradition morphological control; this corroborates the form, not the Pāṇinian rule numbering. [Dhātuparāyaṇa, p.109](https://jainqq.org/explore/004315/109/). |
| 02.0034 ūrṇu | Optional iṭ plus optional ṅit treatment accounts for `UrRunUza-`, `UrRunaviza-`, `UrRunuviza-`. The actual accepted union preserves the alternatives and endings. [7.2.49](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.2.49.htm), [1.2.3](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/1/1.2.3.htm), [6.4.77](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.77.htm). |
| 02.0060 as | Initial as → bhū substitution is licensed before san; `buBUza-` is consistent. [2.4.52](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/2/2.4.52.htm), [7.2.12](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.2.12.htm). |
| 09.0032 ṝ | The three directly printed desideratives support `aririza-`, `arirIza-`, `Irziza-`. [Dhātupradīpa, printed p.126](https://jainqq.org/explore/004319/136/), [7.2.41](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.2.41.htm). |
| 10.0245 am | The source prints the Curādi base **आमयति-ते**. Intrinsic ṇic and ordinary desiderative reduplication support `Amimayiza-`; trace 1.1.73 is a designation and does not introduce another semantic choice. [Bṛhaddhāturūpāvali](https://sa.wikisource.org/wiki/बृहद्धातुरूपावलिः). |
| 10.0341 sah | Dhātupradīpa explicitly prints the Curādi alternatives `sAhayati` / `sahati` and distinguishes other sah entries. The niC-bearing desiderative retains dental s under 8.3.62; the candidate preserves both licensed base branches. [Dhātupradīpa, sah entry 252](https://jainqq.org/booktext/Dhatupradip/004319), [8.3.62](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.3.62.htm). |

One control-only limitation remains: VP's present kam+san output lacks the source-supported short branch, although both actual candidate inputs have it. This review does not certify other kam coordinates by extrapolating from those two accepted unions.

The review used no paid calls, no final model answers, and no outcome-based candidate selection. It does not establish benchmark accuracy or reopen 4D discovery. Earlier completed discovery run IDs and chime receipts remain unchanged.
