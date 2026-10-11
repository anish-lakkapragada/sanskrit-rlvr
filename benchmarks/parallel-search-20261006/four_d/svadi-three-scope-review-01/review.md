# Exact Svādi pṛ, spṛ and smṛ: classical-scope review

The primary sources support a **conservative unresolved-classical-scope hold on exact dictionary codes 05.0013–05.0015**, across all coordinates and recipes. They do not establish a unanimous assertion that every use of these entries is exclusively Vedic. The coordinator adopted this qualified disposition in policy20. This review neither substitutes corrected gold nor changes any frozen question or raw result.

| Installed code | Citation / class | Installed meaning | Master split |
|---|---|---|---|
| 05.0013 | pṛ / Svādi | prītau | test |
| 05.0014 | spṛ / Svādi | prītipālanayoḥ prīticalanayośca | RL train |
| 05.0015 | smṛ / Svādi | prītibalanayoḥ | development |

## Primary evidence and its qualification

The [Mādhavīyā Dhātuvṛtti primary scan, printed page 452](https://sanskritlibrary.org/Sanskrit/Vyakarana/Dhatupatha/mdhvscan/MDhVjpg/madhaviyahdhatuv00sayauoft_bw_0506.jpg) places pṛ prītau immediately before spṛ prītipālanayoḥ, with smṛ given as an alternate reading. Its footnote gives Kṣīrasvāmin's prītibalanayoḥ reading. It quotes Pārāyaṇa as saying **“स्पृणोतिस्मृणोती इमौ छान्दसौ”**, then Svāmin and Kāśyapa as saying **“इमौ पृणोतिश्च त्रयश्छान्दसाः”**. The first attribution restricts spṛ and smṛ; the second includes pṛ. We directly viewed Mādhavīya's report of those authorities; we did not inspect separately surviving editions of Pārāyaṇa or Kāśyapa. The [library's edition note](https://sanskritlibrary.org/Sanskrit/Vyakarana/Dhatupatha/mdhvindx/disp/indexAbout.html) documents the scan collection.

The [Kṣīrataraṅgiṇī primary scan, printed page 238](https://jainqq.org/explore/002433/295) identifies pṛ prītau and pṛṇoti. The [next page, printed 239](https://jainqq.org/explore/002433/296) identifies smṛ prītibalanayoḥ, explains balana as living, and gives spṛ as another reading. Crucially it says **“ते तु छान्दसप्रायौ”**: predominantly Vedic, a weaker claim than exclusively Vedic. The editor proposes pronoun/number corrections and cites Mādhavīya's stronger attributed classification; the proposed corrections retain *prāya*. The image clearly reads spṛ as the alternate even where the site's OCR repeats smṛ. Both pages were visually inspected.

The [Siddhāntakaumudī Svādi section](https://sa.wikisource.org/wiki/सिद्धान्तकौमुदी/प्रकरण‌४१-५०), entries 1259–1260, likewise enumerates pṛ, spṛ and the smṛ reading, then says **“पृणोत्यादयस्त्रयश्छान्दसा इत्याहुः”**. Its attribution, “they say,” should be preserved. We found no direct classical finite-use counterexample in this bounded review; that is not proof that none exists.

This qualification was already recognized in [the earlier lexical scope scan](../search-03.lexical-scope-scan.json), which left these entries unresolved and avoided using them as new hardness leads. The new primary scan strengthens the documented basis for a conservative scope hold. It does not erase the older caution or convert “predominantly” into “exclusively.”

## Narrow predicate and controls

The adopted entry predicate is simply `code in {05.0013, 05.0014, 05.0015}`. It does not depend on tense, recipe, a model answer, or trace 1.3.57. Other homonyms remain unaffected by this predicate: Bhvādi smṛ 01.0919/01.1082, Juhotyādi pṝ/pṛ 03.0004/03.0005, Kryādi pṝ 09.0022, and Curādi pṝ 10.0022. Existing independent holds still apply normally.

[review.json](review.json) records installed identities, master splits, eighteen ordinary/desiderative present controls, current scope results, source URLs and SHA256 hashes of all three inspected scan images. These engine controls establish identity and mechanical behavior, not independent classical licensing. The [reproduction script](../../../../misc/vp_4d_svadi_scope_review.py) accesses inputs and the engine only.

The initial lead mentioned desiderative 1.3.57. Its [Nyāsa commentary](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/1/1.3.57.htm) explicitly names smṛ ādhyāne. An example from that entry does not alone establish an exclusive cintāyām condition or prove a separate Svādi-san engine bug. The broader entry-scope uncertainty is the supported reason for this hold.

## Effects, applied without regard to correctness

The original, wholly unsubmitted pilot08 has three affected smṛ inputs, one in each recipe. Its frozen Astra240 subset has none. Candidate04 has six affected pṛ inputs; only inputs were inspected. The Astra60 cap diagnostic has none. These originals remain immutable; pilot08 will be rebuilt under policy20 using the declared input-only allocation.

| Earlier development job | Affected currently eligible items | Correct | Usable wrong |
|---|---:|---:|---:|
| Opus 5D pilot01 | 1 | 1 | 0 |
| Astra paired 5D pilot01 | 1 | 0 | 1 |
| Opus 4D pilot03 | 2 | 2 | 0 |
| Opus 5D pilot05 | 2 | 2 | 0 |
| Opus 5D pilot07 chunk A | 4 | 4 | 0 |

These ten evaluation rows cover nine distinct questions, including the same pilot01 question evaluated by both providers. No affected item is nonusable. The exact IDs and original input file hashes are in the JSON artifacts. With policy20 applied, 4D pilot03 becomes 172/173 (99.42%); its unresolved-stim sensitivity remains 100% at 172/172. This changes no substantive 4D feasibility conclusion. No new paid call, pilot08 answer access, test-answer access, or shared-file edit occurred in this review.
