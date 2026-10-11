# Independent source review — ending screen 01

**2026-10-07 UTC. Decision: the fixed 96-question development screen may proceed with the saved spelling whitelist and mandatory review of unfamiliar answers.** This is a bounded execution review, not certification of every lexical paradigm or a final benchmark. No model responses, provider APIs or spending ledger were read or changed.

The independent check regenerated all **96 questions / 96 families / 124 canonical forms**, including the complete VP unions and unchanged exact-4D prompts. Every engine path, individually, contains its cell's required rules. Dictionary entries have no explicit inherited prefix or added sanādi, pass the existing scope checks, and retain citation, class and meaning in the prompt. `sampling_cell` is provenance metadata; it is not an extra model-visible coordinate. The JSON records the input, source and alias hashes.

## The four grammatical claims

| Cell | Independent primary evidence | What the evidence establishes |
|---|---|---|
| Luṭ second-person singular | Kāśikā on [7.4.50, tāsasty or lopaḥ](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.50.htm), with **कर्तासि / कर्तासे**; Nyāsa identifies the endings. | The s of tās/as is deleted before an s-initial ending. Both ending sets can be licensed; retaining their union is essential. The selected rare lexical future stems are applications of the rule, not all independently printed examples. |
| Laṅ/Lṛṅ third-person plural | Kāśikā/Nyāsa on [8.2.23, saṃyogāntasya lopaḥ](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.2.23.htm), and [8.4.37, padāntasya](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.37.htm). | A final consonant of the word-final cluster is lost; word-final n is protected from retroflexion. The latter is a prohibition, not an additional surface edit. A logged prohibition does not establish difficulty. The selected finite forms are rule inferences. |
| VidhiLiṅ/ĀśīrLiṅ third-person plural | Kāśikā on [3.4.108, jher jus](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.4.108.htm), directly printing **पचेयुः / यजेयुः**. | The jhi→jus substitution is restricted to liṅ; the general scope includes the benedictive liṅ. It does not apply to every ending set. The paca source control also has an ātmanepada branch and therefore is a control, not a qualifying all-path pilot item. |
| Luṅ singular repair | Kāśikā/Nyāsa on [7.3.96, astisico 'pṛkte](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.3.96.htm), and Kāśikā/Bālamanoramā on [8.2.28, iṭa īṭi](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.2.28.htm). | The first rule supplies īṭ to the eligible apṛkta ending; the second deletes the intervening s specifically after iṭ and before īṭ. Printed positive and negative controls distinguish alāvīt, akārṣīt and alāviṣṭām. Describe this cell as **iṭ-bearing sic with the apṛkta repair**, not all sigmatic aorists. |

The source pages occasionally display an off-by-one rule number in a heading. The linked commentary's sūtra name and content, rather than that inconsistent heading alone, identify the rule. Fifteen downloaded source pages are preserved with hashes in `independent-source-cache/` and the review JSON.

## Concrete answer-union omissions and the remedy

The original canonical keys omit independently licensed spellings. This was found before any pilot responses were inspected.

* **Final doubling:** Kāśikā on [anaci ca](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.47.htm) explicitly extends doubling to a pause; Bālamanoramā on [vāvasāne](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.56.htm) explicitly distinguishes the singleton/doubled t and d alternatives. Thus alūṣīt/alūṣītt and alūṣīd/alūṣīdd are licensed. Applying the general yar scope also yields final dental nn, such as aśokiṣyan/aśokiṣyann. This affects 36 questions and at least 48 missing aliases before combinations.
* **After postvocalic r/h:** [8.4.46](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.46.htm) directly illustrates arka/arkka-type doubling. Applied to selected forms, examples include anardīt/anarddīt, akardīḥ/akarddīḥ and arcitāsi/arccitāsi. There are at least 12 affected questions. The earlier literal `vowel+rC` exclusion covered only the SLP1 character C, not this entire context.
* **Simple internal clusters:** The general anaci-ca condition also supports atṛpyan/atṛppyan and rasyāsuḥ/rassyāsuḥ. Aspiration needs the subsequent assimilation rules: [8.4.53](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.53.htm) for a voiced stop environment and [8.4.55](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.55.htm) for an unvoiced one. Simply copying an aspirated letter twice would be wrong.

The saved `alias-policy.json` addresses these with **172 explicit extra forms across 62 questions**. Canonical VP gold and prompts remain intact. I independently reconstructed the finite alias map from the canonical forms and the source conditions: it matches exactly. Verification accepted all 124 canonical forms and 172 aliases, rejected 320 mutations to stems/endings/nasal place or triple final stops, and rejected an unknown task ID.

The map applies a licensed operation once at each original eligible position and includes combinations of those positions. It excludes doubling r/h themselves, observes the [śar-before-vowel prohibition](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.49.htm), and preserves the original voicing, vowels, ending set and all other characters. It is not a generic duplicate-collapse normalizer.

Existing geminates/cC and original clusters of three or more consonants are not exhaustively expanded. [8.4.50](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.50.htm) has commentary-dependent treatment of longer clusters, while [8.4.51](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.51.htm) explains the option of undoubled forms. Eight questions explicitly flag such residual contexts. Their canonical answers remain usable; an unlisted alternative must be reviewed, rather than presumed incorrect.

## Scope and conditions of the go decision

This remains **dictionary dhātu + exactly four coordinates**, without an added pada choice. Most cells incidentally select entries with a single compatible ending set; future questions include both where licensed. Neither “Kartari” nor the all-path filter permits discarding a valid ending-set branch. Intrinsic Curādi formation follows the supplied dictionary identity; it is not a separately selected operation.

The prompt permits any valid form and does not impose a canonical-spelling restriction. Accordingly:

1. Preserve raw answers and canonical scores, and report the predeclared whitelist score alongside them.
2. Independently adjudicate **every usable unrecognized answer** before calling it a linguistic error or applying the screen's advancement criterion. This includes ordinary-looking alternate stems and lexical readings, not only doubled letters.
3. Unresolved spelling or lexical cases cannot contribute to the eight wrong families, three classes/cells, or a below-90% success claim. Publish the raw denominator and unresolved count; do not silently remove questions.
4. Apply any subsequently established source rule consistently to every affected question and both reference models. Preserve the predeclared score separately from later adjudicated scores.

With those requirements, there are **no unresolved execution blockers**. There remain explicit limits: the 96 lexical paradigms have not each received independent full source certification, the whitelist is finite, and the four mechanisms have not demonstrated difficulty. Source agreement and engine regeneration do not establish a below-90% benchmark.

Recorded alias file SHA-256: `4565d30327e6c958f126b94e9979e2838a69734e9fa14cf86a8567b2c4e3433e`.

Recorded alias helper SHA-256: `95aa681cf454a6f71e63acc4fd34ff52ae9b9341a2a9e6c68050c0a073003825`.
