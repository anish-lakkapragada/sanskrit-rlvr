# Opus final1800: bounded source adjudication

2026-10-08 UTC. All **214 usable mismatches** and **five refusals** have individual records in [Anthropic-review.json](Anthropic-review.json). This is an additive source review; raw responses, membership, canonical scores and frozen spelling scores remain unchanged.

The review rejects **208 submitted forms**, leaves **six unresolved**, and accepts no additional answer. It does **not** independently certify every successful answer, every canonical gold alternative, or an exhaustive Sanskrit paradigm.

## The 187 short-stem errors

| Supplied literal-a family | Errors | Submitted stem | Required ordinary stem |
|---|---:|---|---|
| Cada | 66 | छादय- | छदय- |
| laja | 62 | लाजय- | लजय- |
| kuha | 40 | कोहय- | कुहय- |
| paWa | 11 | पाठय- | पठय- |
| pada | 8 | पादय- | पदय- |

These are independently supported incompatibilities in the actual answers. For ordinary kathādi/Curādi derivation, deleting the literal final **a** before intrinsic **ṇic** does not license strengthening a vowel that only becomes penultimate after that deletion. The classical kathādi explanation explicitly invokes the deleted vowel's retained positional effect. The affected lexical stem is retained across the nine selected non-aorist tense/mood families; an auxiliary in the periphrastic perfect does not change it. The primary rule is [6.4.48 with its commentary](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.48.htm), read together with the previously inspected [SK adanta section](https://sa.wikisource.org/wiki/सिद्धान्तकौमुदी/प्रकरण‌५१-६०).

The exact lexical controls matter. Printed SK1938 p.238 and Kṣīrataraṅgiṇī p.333 entry321 support **छदयति** for literal-final-a **छद**, distinct from the nasal-marker Cada~ and Cadi~ entries. A conflicting electronic long-vowel transcription is documented in the prior reading clarification; this review does not pretend that every edition agrees. Madhavīya p.573 supports **लजयति** and treats alternative laji readings separately. Printed SK237 supports **पदयते**, **कुहयते**, and the intrinsic middle-pada group. The aspirated **पठ** entry is printed in SK236; its short finite stem is a general-rule inference, not a claim that all its paradigms were printed. Exact cached source paths and hashes are bound through the reference pack and reading clarification.

The alternative **puK** derivation does not rescue these answers. It lengthens the **final** a and adds **p**; it does not license the model's p-less first-vowel changes. None of the 214 answers matches any of the adopted19 exact puK additions.

A diagnostic comparison confirms that replacing only the identified wrong stem in **186/187** answers yields one canonical form. This is a way to locate the mistake, not a new spelling-normalization rule. Index1075 also has a wrong perfect auxiliary, **cakravahe** instead of **cakṛvahe**; the **koh/kuh** discrepancy already suffices to reject that answer. Every task and answer is individually mapped in the JSON.

## Thirteen other-adanta aorists

| Family | Errors | Incompatible change |
|---|---:|---|
| anka | 3 | āñcak- → āñcik- |
| anga | 5 | āñjag- → āñjig- |
| anDa | 2 | āndadh- → āndidh- |
| ansa | 2 | āṃsas- → āṃsis- |
| BAma | 1 | ababhām- → abībham- |

[7.4.93](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.93.htm) expressly excludes **aglopin** stems from san-like reduplicative vowel changes; its commentary supplies **अचकथत्** as the exclusion example. [7.4.2](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.2.htm) separately blocks the shortening seen in the BAma answer. Printed SK representatives **आञ्चकत्**, **आञ्जगत्**, **आन्दधत्**, and **अबभामत्** support the stem judgments. The ansa aorist follows the same general-rule derivation from the specified dental-s entry; no directly printed full ansa aorist paradigm is claimed. Person/number endings do not license the incompatible vowel changes.

## Fourteen broad cases

Eight answers have concrete rule or exact-lexeme conflicts:

| Index | Answer | Finding |
|---:|---|---|
| 90 | डिडेपिथ | Kutādi ṅit treatment blocks the proposed guṇa; डिडिपिथ. |
| 181 | कुथ्नीत | Wrong optative/person ending for second-person plural; कुथ्नीयात. |
| 764 | ईषेथाः | Uses the middle ending of another reading; supplied उञ्छे entry is ईषति. |
| 949 | द्ययाम | ai→āy requires the long stem vowel; द्यायाम. |
| 992 | रिरिन्व | Omits required ṇatva; रिरिण्व. |
| 1025 | दुर्वतः | Omits the root-internal lengthening of 8.2.78; दूर्वतः. |
| 1104 | चेलानि | Deletes a lexical l; supplied cella is distinct from cela. |
| 1686 | मीर्यास्म | Labial-conditioned vocalic-r change requires ū; मूर्यास्म. |

The JSON supplies rule chains and primary locators for each. In particular, [8.4.64](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.64.htm) requires a preceding consonant for optional sonorant deletion. It cannot reduce the two lexical l consonants after **e** in cella to one.

The following **six remain unresolved**, with no answer credit or rejection silently imposed:

| Index | Answer | Unresolved issue |
|---:|---|---|
| 229 | असरन् | Kāśikā3.1.56 explicitly supplies सृ→असरत्; Madhavīya restricts this aṅ branch to Juhotyādi. Exact Bhvādi applicability needs adjudication. |
| 437 | जम्भते | Primary sources support jabh in this meaning with num and middle endings, but the supplied jaBa~ citation's marker/entry identity differs. |
| 481 | अरेबामहि | A primary rebu-type movement entry has middle forms; identity with supplied rebf~/plavagatau is unverified. |
| 495 | खुण्डिताध्वे | Rare Kuqi~/gativaiKalya entry's exact source/pada not independently verified. |
| 566 | असलताम् | No established aṅ license for the supplied vocalic-r-marked zal-f~ entry; exact lexical/source enumeration remains incomplete. |
| 1186 | कण्डिष्ये | Primary kadi/made has middle forms; reconciliation with the supplied unaccented kaqi~ citation remains necessary. |

No unspecified grammatical school is used as an automatic exclusion. New Jainqq scan requests returned HTTP403; for the broad lexical leads, the review explicitly distinguishes existing cached primary-book OCR from new visual inspection. Earlier visually inspected hard-family sources are reused under their existing limitations.

## All five refusals are provider cyber-filter false positives

Indices **20, 532, 666, 1367, 1492** have no final answer. All five raw envelopes explicitly report **stop_details.category = cyber**. Four returned summaries discuss Sanskrit grammar; one has no summary. All five prompts already say **Sanskrit verbal root (dhatu)** and clearly request grammatical conjugation.

This establishes a provider cyber-filter false positive on harmless grammar tasks. It does not identify the exact trigger or prove that the English word “root” caused it. Three task glosses concern stealing, but two do not; that correlation is not a causal explanation. The JSON retains the exact task IDs and provider stop details. These remain recorded nonanswers on the fixed1800 denominator, separately from submitted linguistic mistakes; there was no retry or replacement.

## Interpretation and limits

The original canonical and finite-spelling result remains **1581/1800 = 87.8333%**. If all six unresolved usable cases were ultimately accepted, that would be **1587/1800 = 88.1667%**. Also hypothetically crediting the five refusals gives **1592/1800 = 88.4444%**; this is a sensitivity calculation, not a measured score.

The most conservative narrow bound uses only the independently supported187 short-stem errors: even crediting **every other mismatch and refusal**, the result would be **1613/1800 = 89.6111%**. That is a conditional source-uncertainty upper bound, not full benchmark certification.

Difficulty is concentrated. Cada+laja supply **128/219 = 58.45%** of all noncorrect cases; the five short-stem families supply **187/219 = 85.39%**. Coverage of755 families consequently does not establish evenly distributed difficulty across755 families. The reported family-dependent standard error remains about **4.95 percentage points**, so the earlier below1-point precision requirement is not met.

No gold key, task membership, prompt, paid dependency, ledger record, model call, or training state was changed.
