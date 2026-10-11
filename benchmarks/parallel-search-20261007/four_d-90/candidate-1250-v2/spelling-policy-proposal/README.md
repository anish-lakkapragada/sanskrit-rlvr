# Candidate v2: finite spelling-policy proposal

Date: 2026-10-07. **The existing bounded spelling rules transfer to this finite candidate.** This directory is a separate, pre-output proposal. It changes no canonical key, prompt, candidate membership, runner, ledger, or frozen ending-screen artifact. It does not authorize evaluation or declare the benchmark ready.

The policy accepts **2,264 additional task-specific spellings across 829 of 1,250 questions**, alongside all **2,248 canonical forms**. It uses the **unchanged ending-screen `sites()` rules and builder**, with only panel-specific metadata replaced. There are at most three independently eligible original positions in any canonical form. Aliases are enumerated once from those positions; no rule is recursively applied to newly produced text.

## Why the transfer is licensed

The relevant source conditions concern the sound sequence and pause, rather than the root's verb class, aorist status, or tense. The candidate's Curadi-heavy composition does not change their applicability:

- Optional final dental **n / t / d** doubling at pause, preserving place and the canonical voicing branch. Every such site in this candidate follows a vowel, so this transfer needs no new final-cluster interpretation. [Kāśikā on anaci ca](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.47.htm), [Bālamanoramā on vāvasāne](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.56.htm).
- Doubling an eligible consonant after **vowel + r/h**, excluding r/h as the doubled target and observing the sibilant-before-vowel prohibition. [aco rahābhyāṃ dve](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.46.htm), [śaro ’ci](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.49.htm).
- Doubling the first eligible consonant in a **postvocalic, original two-distinct-consonant cluster**, with first-copy deaspiration where required. The existing exclusions and the original-position-only bound remain. [anaci ca](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.47.htm), [jhalāṃ jaś jhaśi](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.53.htm), [khari ca](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.55.htm).

No additional lexical branch, vowel change, pada choice, nasal retroflexion, arbitrary consonant substitution, or global duplicate-collapse rule is added. The primary-source snapshots and their previously reviewed hashes are referenced in `transfer-review.json`.

## Concrete controls

`controls.json` contains 13 source-rule applications, including a set spanning **all ten classes and all ten tenses/moods**. These are applications of the cited generic rule to oracle forms, not claims that each rare form is printed in a commentary. Examples:

| Class / tense | Canonical | Listed alias | Mechanism |
|---|---|---|---|
| Curadi / Lat | छदयध्वे | छदयद्ध्वे | First copied aspirate is deaspirated |
| Bhvadi / Lan | ऐक्षे | ऐक्क्षे | Simple postvocalic cluster |
| Kryadi / Lot | कृणीताद् | कृणीताद्द् | Final stop doubling |
| Tudadi / Lut | तुम्पिता | तुम्म्पिता | Simple postvocalic cluster |
| Adadi / AshirLin | जागर्यास्म | जागर्य्यास्म | Postvocalic r-conditioned doubling |
| Curadi / Lan | अरहयन् | अरहयन्न् | Final dental n remains dental |

The exact SLP1 forms, transliterations, task IDs and per-alias derivation witnesses are saved; the scorer uses those finite strings, not this illustrative table.

## Remaining contexts and fair error reporting

**53 questions contain 83 flagged occurrences** of existing gemination/cC or original clusters of three or more consonants. They retain canonical answers and any independently licensed aliases at other eligible sites. `unresolved-contexts.json` identifies each question and sequence. The general longer-cluster closure is not inferred here; the previously reviewed commentary differences remain. [triprabhṛtiṣu śākaṭāyanasya](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.50.htm).

This flag list is not an exhaustive list of all potentially acceptable unlisted Sanskrit spellings. **Every usable unrecognized response must receive source adjudication before it supports an error or advancement claim**, whether or not its question is among those 53. Preserve canonical-only, predeclared-whitelist, and later adjudicated scores separately. Keep unresolved cases explicit and apply any established correction symmetrically across every affected task and model. Do not silently discard questions.

`scorer.py` provides a hash-bound `FiniteScorer().grade(output_text, task_id)`. It uses the existing answer extraction and normalization, accepts only that task's canonical forms or listed aliases, and returns `unrecognized_pending_source_review` for unlisted parsed answers. Unknown IDs and changed input/policy hashes fail closed. Transport usability, refusals and truncations still belong to the execution layer.

## Verification and scope

An independent regex-based reconstruction matched all 1,250 finite alias sets. Offline verification accepted all 2,248 canonical forms and all 2,264 aliases; routed 1,250 unlisted changes to adjudication; rejected automatic acceptance of 66 final-n retroflexion mutations and 158 triple-final-stop mutations; and checked unknown-ID and cross-task isolation. These negative checks establish whitelist boundaries, not philological judgments about every invented string.

The policy SHA-256 is `b56b2660ddc23b33e6a55596ed49c37e05d2bc087d098b334e97e2f9187352e3`. It is bound to candidate task SHA-256 `e7800eb7093a7531dbd92b6965fdbfc90a5260d506b78d698fa586cc7319a1e5`. Full receipts are in `verification-receipt.json`.

This is bounded spelling-rule clearance. It does not certify all lexical paradigms, supply held-out performance evidence, or resolve family-dependent precision. No provider API or model response was accessed.
