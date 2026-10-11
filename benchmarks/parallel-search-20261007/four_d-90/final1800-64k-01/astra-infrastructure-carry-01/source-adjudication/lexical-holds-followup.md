# Four lexical holds: source follow-up

2026-10-08 UTC. This is an additive source review; historical questions, responses, scores, and the previous review remain unchanged. The accompanying JSON maps every judgment to exact task IDs, paired answers, source snapshots and hashes. All 44 original frozen dependencies still match.

**Two Opus answers are licensed by the primary sources, but their public inputs and existing keys need repair. One answer is rejected, and one remains unresolved.** The two corrections cannot be implemented by merely expanding the accepted answer sets: the old keys also credit unsupported answers from Astra.

| Index / dictionary entry | Opus answer | Source disposition | Historical key / Astra answer | Required action |
|---|---|---|---|---|
| 481, `01.0248 rebf~`, प्लवगतौ | अरेबामहि | Licensed middle form; defective citation | अरेबाम | Repair citation and revoke old P key in a new source-backed version |
| 495, `01.0946 Kuqi~`, गतिवैकल्ये | खुण्डिताध्वे | Licensed middle form; defective citation | खुण्डितास्थ | Repair citation and revoke old P key in a new source-backed version |
| 566, `01.0253 zalf~`, गतौ | असलताम् | Unresolved lexical reading; answer has no established aorist derivation | असालिष्टाम् | Retain input/source hold |
| 1186, `01.0418 kaqi~`, मदे | कण्डिष्ये | Rejected for the supplied distinct P citation | कण्डिष्यामि | Retain key |

## Reb and khund: source-supported forms, inconsistent inputs

The printed *Dhātupradīpa* gives **रेबते** on printed page 33 ([scan 43](https://jainqq.org/explore/004319/43)). Printed page 40 explicitly distinguishes the earlier stop-final **reb/pleb** from approximant-final **rev/plev**, then closes the section as middle verbs with anudātta it-markers ([scan 50](https://jainqq.org/explore/004319/50)). Both scans were visually inspected. Ordinary imperfect first-person plural therefore yields **अरेबामहि**: aṭ augment, Bhvādi śap, middle mahiṅ, and stem-vowel lengthening before m. This does not introduce a causative or other extra operation.

The printed *Kṣīrataraṅgiṇī* states **खुडि गतिवैकल्ये । खुण्डते**, separately identifies the Curādi breaking sense, and closes this section as udātta roots with anudātta it-markers ([scan 110, printed p.53](https://jainqq.org/explore/002433/110)). This scan was also visually inspected. The middle periphrastic-future second-person plural **खुण्डिताध्वे** follows num, iṭ+tās, and dhve. The *Siddhāntakaumudī* explicitly supplies the structurally identical **एधिताध्वे** under 8.2.25; its cached primary transcription is `sk-primary-text.json`, key `82025`.

The public renderer preserves the relevant accent. `rebf~\` renders **रेबृँ॒**, whereas the supplied `rebf~` renders **रेबृँ**. Likewise `Kuqi~\` gives **खुडिँ॒**, but the prompt supplies **खुडिँ**. This is a concrete lexical-data defect, not merely an invisible fifth coordinate. The primary classifications license middle endings through [1.3.12](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/1/1.3.12.htm).

Recommended prospective corrections are **रेबृँ॒ → अरेबामहि** and **खुडिँ॒ → खुण्डिताध्वे**, retaining each task's other four coordinates, class, and meaning. No inspected source licenses a P+A union for these exact lexemes. In particular, a different Curādi entry cannot license the P answer for the Bhvādi limping entry.

Both Astra responses equal the original P keys and were scored correct. Any source-conditioned retrospective annotation must therefore allow **correct-to-incorrect as well as incorrect-to-correct** changes. A one-directional answer-admission tool is unsuitable. Because the historical prompts themselves are inconsistent, preserve their raw grades and mark the inputs defective; do not claim that old responses were obtained from repaired prompts. Each affected code occurs once in the current1800, but the correction applies uniformly to its other ordinary conjugation cells in future data.

## Kaḍ: a genuinely distinct P reading

The primary *Siddhāntakaumudī* transcription says **कड मदे । कडति । कडि इत्येके । कण्डति** (`sk-primary-text.json`, key `72005`). The visually inspected *Mādhavīyadhātuvṛtti*, printed p.116, gives the P reading and distinguishes the previously discussed **कण्डते**; printed p.106 confirms that separate middle entry. The [accentuated Dhātupāṭha](https://sanskritdocuments.org/doc_z_misc_major_works/dhatupatha_svara.html) likewise distinguishes `1.316 कडिँ॒` from `1.418 कडिँ`.

Thus the benchmark's visible **कडिँ** has a source-supported P reading. The alternative middle citation would be visibly **कडिँ॒**, which was not supplied. With ordinary future i+sya and first-person singular mi, the licensed answer is **कण्डिष्यामि**; **कण्डिष्ये** selects the separate middle entry. The rejected judgment relies on positive evidence for both readings and their distinction, rather than on an engine default. A future prompt can explain that displayed citation accents identify the dictionary entry without adding a task coordinate.

## Ṣalṛ: retain the lexical hold

The editorial inventory claims `01.0253 षलृँ` is a *Kṣīrataraṅgiṇī* alternate of the śel/sel entry. The visually inspected [scan141, printed p.84](https://jainqq.org/explore/002433/141) instead has **शेलृ** with a **सेलृ** variant; [scan142, printed p.85](https://jainqq.org/explore/002433/142) separately has **सल**. The accentuated Dhātupāṭha similarly separates śel/ṣel from ṣal. These passages do not establish the benchmark's exact short-a plus ṛ-marker citation.

The submitted **असलताम्** has no complete licensed aorist derivation in the evidence reviewed. In particular, the aṅ prescription [3.1.55](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.55.htm) concerns specified root groups or the vocalic-l marker, not a generic vocalic-r marker. But an apparently wrong answer does not resolve a questionable input. Keep this task unresolved until its exact reading is independently sourced; do not silently substitute an e-vowel entry or another marker. Apply the same identity hold to repository `01.0759 zalf~` if it is used elsewhere.

## Limits and provenance

The two accepted complete forms are productive derivations from printed lexical classifications and primary rules; this review does not claim each full inflection is separately printed. The unresolved ṣalṛ result reflects a bounded search of specific editions, not proof that no other edition contains that reading. No full-paradigm or full755-family certification follows.

The editorial inventory snapshot is `lexical-holds-sources/ashta-dhatu-data.json`, retrieved from [ashtadhyayi-com/data](https://raw.githubusercontent.com/ashtadhyayi-com/data/master/dhatu/data.txt). Its `data[].baseindex` identifies entries; `pada` is A/P/U. Its citation strings often omit accents, so they cannot independently establish accent completeness. It corroborates the two A classifications but is not a substitute for the primary scans. The JSON records all downloaded source hashes, exact prompts, paired observations, input hashes, source limits, and repair proposals. No changes were made to gold, public prompts, source-adjusted scores, the ledger, or any frozen dependency.
