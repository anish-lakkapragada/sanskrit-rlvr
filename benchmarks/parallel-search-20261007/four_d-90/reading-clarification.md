# Two lexical clarifications for the 1,250-task proposal

Date: 2026-10-07. This is an additive, input-only review. No model answers, paid APIs, tasks, keys, source holds, or frozen artifacts were changed. Exact affected item IDs, source snapshots, hashes, and the marker diagnostic are in `reading-clarification.json`.

**Recommendation: retain 10.0481 छद under its explicit literal-final-a reading; prospectively remove 10.0108 मार्ग from the adanta sampling stratum.** The parent has selected this approach for a separate candidate version. Neither finding demonstrates that a current answer is wrong. The second finding concerns the grammatical justification of the allocation.

## 10.0481 Cada: the printed sources support the short stem

The newly downloaded and visually inspected **1938 Siddhāntakaumudī, printed page 238**, gives short **छदयति** in its alternative entry for छद अपवारण. **Kṣīrataraṅgiṇī, printed page 333, entry 321**, likewise gives छदयति and explicitly contrasts other छद entries with long छादयति. The Madhavīya alternative entry in its adanta section supplies a third lexical witness. [SK scan](https://jainqq.org/explore/002377/242), [Kṣīrataraṅgiṇī scan](https://jainqq.org/explore/002433/390), [Madhavīya scan, printed page 575](https://sanskritlibrary.org/Sanskrit/Vyakarana/Dhatupatha/mdhvscan/disp/index.php?page=629).

This materially narrows the earlier concern: the long form in the [Wikisource SK transcription](https://sa.wikisource.org/wiki/सिद्धान्तकौमुदी/प्रकरण‌५१-६०) is not reproduced by the printed SK edition checked here. It is insufficient evidence for inserting a blanket long-vowel branch into the answers. This review does not establish that every edition agrees or that the transcription is universally erroneous.

The exact declaration should be:

> Entry 10.0481 is literal-final-a छद (SLP1 `Cada`), Curadi, अपवारणे. Its final अ belongs to the lexical entry, rather than serving as an anubandha. Use the adanta reading attested in Kṣīrataraṅgiṇī entry 321 and the 1938 Siddhāntakaumudī, printed page 238.

The full citation matters. Class and meaning alone do **not** distinguish all homonyms: the dictionary separately contains 10.0370 `Cada~`, also Curadi / अपवारणे, and 10.0062 `Cadi~` / संवरणे. Those are distinct lexical specifications, not freely interchangeable answers to the supplied entry. The existing public task supplies the full citation with anubandha markers; a release source table should make the literal-a convention and lexical mapping explicit. This declaration does not introduce another conjugation coordinate.

**Disposition:** keep its 47 proposed non-aorist questions. No missing long-vowel answer branch has been demonstrated for this exact reading. The direct witnesses establish the lexeme and representative short present stem; they do not independently certify all 47 finite-form unions. Ordinary phonological/spelling variants remain a separate scoring-policy audit.

## 10.0108 mArga: supported lexeme, weak adanta classification

Madhavīya, printed page 546, reports a separate मार्ग root reading under the संस्कारगत्योः discussion and explicitly supplies मार्गयति. The meaning distinguishes it from the separate अन्वेषणे entry. This gives positive lexical evidence for the task's root identity. [Primary scan](https://sanskritlibrary.org/Sanskrit/Vyakarana/Dhatupatha/mdhvscan/disp/index.php?page=600).

It does not establish the literal-final-a adanta classification used by the sampling stratum. The [Sanskrit Library scholarly index](https://sanskritlibrary.org/Sanskrit/Vyakarana/Dhatupatha.old/mdhvindx/disp/mdhv_index.html) indexes this reading as मार्ग् with marker अ, while separately recognizing genuine literal-a entries such as the relevant छद variant. The index is corroborating analysis, not a substitute for the primary commentary. Operational engine spelling ending in `a` cannot by itself certify that a root belongs to a grammatical adanta class.

As a sensitivity diagnostic, I independently regenerated all nine Kartari/Lun person-number combinations using `mArga` and marker-only `mArga~`, each with ordinary Curadi settings. All nine canonical answer unions were identical, including the four selected questions. This demonstrates that this particular engine marker distinction does not change the candidate's aorist unions. It is **not** a source proof, a license to change the input, or a comparison against dictionary entry 10.0384, which also has a different meaning and sub-classification. No specific missing answer branch was established.

**Disposition:** uniformly exclude `code == 10.0108` within the `other_adanta_aorist` stratum and replace all four selected questions in a new version. Preserve v1. This avoids weakening the intended grammar-defined predicate merely to retain four questions; it does not declare मार्ग an invalid root. The excluded IDs are:

- `cart4-f7f2309da497511216496756`
- `cart4-6dd1588a4b1640d80703ee34`
- `cart4-bdb23e2c7f64ec730712a631`
- `cart4-3d2d6f531518d162ce109512`

## Capacity after the additional exclusion

After the already declared ऊन / मिश्र / सङ्ग्राम holds and this prospective मार्ग exclusion, the other-adanta-aorist test pool has **21 families, 189 valid Kartari/Lun tuples, and 188 fresh tuples at the scale census**. All remaining families have at least eight fresh tuples. A 100-question quota remains feasible with 16 families contributing five questions and five contributing four.

Retaining छद leaves the short-adanta non-aorist pool at **14 families, 1,134 valid tuples, and 1,119 fresh tuples**. Its quota remains 650. Dropping the four मार्ग questions alone leaves 1,246 tasks across 535 families; replacing them within the same remaining 21-family pool restores **1,250 tasks across 535 families**, with the original 650 / 100 / 500 cell quotas and 12% overall Lun share. The replacement version still needs its ordinary independent mechanical check and current-history freshness check.

These are supply and source-mapping findings, not full source certification, held-out performance evidence, or proof of a family-dependent standard error below one percentage point. No final benchmark freeze is recommended by this supplement alone.
