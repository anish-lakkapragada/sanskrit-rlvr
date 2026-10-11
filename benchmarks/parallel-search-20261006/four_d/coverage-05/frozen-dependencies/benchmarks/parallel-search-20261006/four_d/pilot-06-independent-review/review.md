# Independent review of ordinary 4D pilot 06

**No concrete source or mechanical blocker found in the frozen 96-question draft.** This review supports a small grammar diagnostic. It does not endorse difficulty, authorize payment, or qualify a benchmark.

The reviewed [panel](../coverage-05/pilot-06.questions.json) has SHA256 `ed0d22a7bb2a68e220259ae1dd98ad19f8425e378301ee57d5bfd3d9480d0a7b`. It contains 48 development families, each with one Lot target and one Lat, Lan, or VidhiLin control; only lakara changes within a pair. Family quotas are Adadi 9, Juhotyadi 2, Svadi 8, Rudhadi 8, Tanadi 1, and Kryadi 20. There are 24 dual and 24 plural pairs, all Kartari/Uttama. The revision from two to one Tanadi families follows input novelty constraints, not outcomes.

## Why the contrast is grammatical

Nyasa explicitly explains that [3.4.92](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.4.92.htm) assigns p-it status to the first-person imperative ending, not to āṭ itself. It connects the resulting absence of ṅ-it status to guṇa. This complements [1.2.4](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/1/1.2.4.htm), which assigns ṅ-it treatment to an ap-it sārvadhātuka. The explanation and examples cover both padas.

[Kāśikā 6.4.111](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.111.htm) limits the weak a-deletion in śnam/as to a following k/ṅ-it sārvadhātuka. [6.4.113](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.113.htm) likewise conditions the long-ī alternation of śnā and eligible reduplicated stems on a consonant-initial k/ṅ-it ending, with the stated ghu exception. Its Bālamanoramā section directly lists the differing first-person present and imperative forms of mā. These support retaining the stronger stem in the proposed imperative targets.

Guṇa in the other branch follows the relevant suffix/root conditions in [7.3.84](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.3.84.htm) and [7.3.86](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.3.86.htm). This is not a rule that every segment of the imperative must match a present strong stem: other rules retain their own phonological conditions. For example, [7.3.92](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.3.92.htm) separately restricts the tṛṇah im augment and prints the first-person imperative without it.

## What was checked

All 96 tasks independently regenerate under policy 21 and pass both Cartesian and shared development validators. All 48 pair mappings and number/class/tense quotas pass. There are 63 target and 68 control derivation paths. Every target path has 3.4.92; none of the control paths does.

The broader 120-target development supply and its 120 present controls also regenerate. Every target derivation lacks the investigated weak changes 6.4.111/113/116/34/107. Eight additional same-root, third-person-dual imperative controls lack 3.4.92, providing negative person controls. These were derived offline and do not change the proposed panel.

For every reviewed task, the union of separately audited Parasmaipada and Atmanepada derivations equals the stored unspecified-pada key. The panel contains 62 P-only, 8 A-only, and 26 both-pada questions. The prompt retains four coordinates and requests one possible form; the audit does not add a pada choice. Kartari does not itself mean Parasmaipada. Root/meaning conditions remain governed by [1.3.12](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/1/1.3.12.htm), [1.3.72](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/1/1.3.72.htm), and [1.3.78](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/1/1.3.78.htm).

## Interpretation limits

- A target trace can still contain 1.2.4 for a class suffix. Absence of that ID from the entire trace is not the test of ending p-it status.
- Stumbh/skumbh have both śnā and śnu under [3.1.82](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.82.htm). The panel correctly retains both. A union-level “6.4.113 branch” label therefore need not describe every accepted answer.
- Optional weak forms must remain accepted: u-retention/deletion follows [6.4.107](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.107.htm), and hā has the short/long-i alternatives described at [6.4.116](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.116.htm). No variants were removed to sharpen difficulty.
- Changing lakara also changes endings and augment/optative morphology. A later paired accuracy difference would be evidence about this combined contrast, not an isolated causal estimate of p-it processing.
- Primary rule review plus full regeneration does not independently certify every lexical form against a printed paradigm. Exact-history novelty is documented by construction; this review did not repeat that history scan.
- The 156 target test tuples from 78 families are too few for a standalone 500+ benchmark or sub-one-percentage-point precision. No model outputs informed this review.

[Machine-readable review](review.json), [full panel derivations](panel-regeneration-audit.json), [120-pair supply audit](supply-derivation-audit.json), [negative controls](negative-person-controls.json), and [primary-source notes](sources/index.json) preserve the evidence. Primary pages were read through the web tool; a direct HTTP cache attempt returned 406, so no complete local HTML cache is claimed. No shared code, source policy, proposed panel, or frozen pilot 08 dependency was changed.
