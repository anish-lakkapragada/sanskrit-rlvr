# 4D pilot 01: grammatical supply and a fresh calibration panel

The frozen pilot has **120 new development questions from 113 dhatu families**. It uses a dictionary dhatu and exactly lakara, prayoga, purusha, and vacana. No model call has been made by this worker. This is a pilot, with no empirical claim yet about 79–81% accuracy or final benchmark readiness.

Each task is generated directly from the dictionary entry's `dhatu`. The shared adapter writes `task_type=cartesian_4d` and `prompt_version=cartesian-4d-v1`, rendering `prompts/v2/vp_task_eval.txt` exactly. There are no derivation, prefix, or pada fields. Class-inherent Curadi morphology comes from the dictionary class; it is not an added operation. For roots permitting more than one ending set, all VP forms remain acceptable and the model supplies one form.

The coordinate menu is the ten classical lakaras (Lat, Lit, Lut, Lrt, Lot, Lan, VidhiLin, AshirLin, Lun, Lrn), Kartari or semantically screened Karmani, all three persons, and all three numbers. Bhave and Vedic Let are excluded. Passive roots must have one of the exact transitive meanings in the generator's documented allowlist; arbitrary voice tuples are not presumed grammatical.

## Pilot sampling

The ten cells are grammar predicates, not lists of model mistakes. Historical development group results motivated some predicates. Freshness is checked against the original 6,687 tasks and all 6,000 discovery questions, including exact model-visible lexical identity rather than just IDs. A second check found no overlap with previously submitted pure 4D components in the iterative campaign. Reserved-test model answers were not read.

The seed is `2026100604`. Selection first protects scarce grammatical supply, then prioritizes new families, balanced person/number, less represented classes, and tense coverage, with SHA256 tie-breaking. At most two questions share a family. Every chosen tuple is regenerated from VP 0.4.0; historical SQLite is opened read-only and provides only candidate coordinates and grammar traces.

| Grammar cell | Questions | Motivation |
|---|---:|---|
| Internal r/v-conditioned lengthening | 12 | Rule 8.2.78; strong but narrow historical lead |
| Svadi perfect | 12 | Lexical class and perfect stem formation |
| Other athematic perfect | 6 | Broadens classes beyond the narrow Svadi lead |
| Perfect reduplication changes | 12 | Samprasarana and vowel-initial reduplication; includes periphrastic auxiliaries |
| Divadi sigmatic aorist | 12 | Class-specific aorist choice and stem treatment |
| Aorist consonant changes | 12 | Consonant interaction and conditioned retroflexion |
| Athematic present system | 18 | Weak-stem and reduplicative formation across present, imperfect, imperative, optative |
| Dictionary Curadi futures | 12 | Inherent class morphology across two futures and conditional |
| Transitive Curadi nonpresent passive | 12 | Optional nonpresent stem treatment with licensed passive semantics |
| Primary benedictive stem changes | 12 | Vowel/cluster treatment without added derivation |

| Distribution | Counts |
|---|---|
| Lakara | Lit 31; Lun 25; AshirLin 19; Lut 13; Lot 7; VidhiLin 6; Lan 6; Lat 5; Lrt 4; Lrn 4 |
| Prayoga | Kartari 108; Karmani 12 |
| Purusha | Prathama 40; Madhyama 40; Uttama 40 |
| Vacana | Eka 40; Dvi 40; Bahu 40 |
| Gana | Curadi 30; Kryadi 14; Svadi 12; Divadi 12; Bhvadi 11; Tudadi 11; Adadi 11; Rudhadi 10; Juhotyadi 7; Tanadi 2 |

Maximum concentration is 25.83% for a lakara, 25% for a gana, and 1.67% for a family. Aorist accounts for 20.83%, and the narrow lengthening cell accounts for 10%.

## Audit and sources

Mechanical regeneration, identity, split membership, complete engine variant sets, transliteration round-trips, and prompt hashes pass for all 120 questions. Twenty-two independently transcribed primary-commentary examples pass local VP verification. They cover vowel lengthening, athematic stems, reduplication, sigmatic aorists, retroflexion, and passive nonpresent variants. These checks are recorded in `pilot-01.audit.json` and `source-audit-01.json`.

The primary sources are [8.2.78](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.2.78.htm), [6.1.10](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.1.10.htm), [6.4.113](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.113.htm), [7.4.62](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.62.htm), [7.4.70](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.70.htm), [3.1.36](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.36.htm), [3.1.44](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.44.htm), [8.3.78](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.3.78.htm), [6.4.51](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.51.htm), and [6.4.62](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.62.htm).

Representative examples independently support the constructions. They do not certify every rare lexical form. Model/oracle disagreements require inspection, especially dictionary interpretation, pada alternatives, vowel quantity, optional variants, and nasal spelling. Prior unresolved nested yaN/Ric/san contexts are not selected constructions here; all Bhave is excluded. No pilot membership was chosen using its own model outcome.

## Supply and the next decision

`supply-01.json` counts grammar-defined candidates across fresh development, the full unchanged 1,000-family master test split, and the legacy two 500-family test suballocations, without reading test answers. The **full master test split** has **nine lengthening families**, **14 Svadi families**, and **15 transitive Curadi families in the narrow passive cell**. At six questions per family these cells supply at most 54, 84, and 90 tasks respectively. Their combined 30% pilot weight cannot be copied exactly into a 1,000-task release under that diagnostic ceiling. Six per family is a proposed diversity diagnostic, not a user-mandated cap. The coordinator may revise the legacy 500/500 suballocation before final exposure; this worker has not altered any assignment. The per-cell counts overlap and are not a jointly feasible sample.

| Cell | Full test tuples | Full test families | Capacity at six per family |
|---|---:|---:|---:|
| Internal lengthening | 756 | 9 | 54 |
| Svadi perfect | 126 | 14 | 84 |
| Other athematic perfect | 954 | 106 | 636 |
| Perfect reduplication changes | 741 | 83 | 495 |
| Divadi sigmatic aorist | 386 | 43 | 258 |
| Aorist consonant changes | 474 | 88 | 333 |
| Athematic present system | 1,837 | 104 | 624 |
| Dictionary Curadi futures | 5,778 | 205 | 1,230 |
| Transitive Curadi nonpresent passive | 270 | 15 | 90 |
| Primary benedictive stem changes | 666 | 74 | 444 |

The pilot intentionally tests these narrow leads alongside broader constructions. Results should determine whether broader grammatical intersections merit a second fresh pilot. A low pilot aggregate would not by itself establish a transportable benchmark. If broader cells remain near the historical 95% accuracy, a diverse 80% benchmark may be unsupported in this exact 4D scope. Any revised predicates must be frozen before fresh calibration; final membership must never be chosen by same-item failure.

Proposed release constraints, to freeze after feasible-supply optimization and before final answers: at least eight lakaras, at least eight ganas, maximum 25% per lakara, maximum 30% per gana, aorist at most 25%, all persons and numbers at least 20% each, and at least 200 families for a 1,000-task release. Six tasks per exact-citation-plus-gana family is a useful initial diagnostic ceiling, subject to explicit coordinator revision with concentration and family-aware uncertainty reported. Keep the master development/test/RL assignments unchanged. The legacy initial/future test suballocation may be revised by the coordinator before final exposure. RL questions must be regenerated from the distinct existing `rl_train` families; none of this development pilot is an RL export.

Request Opus 5.5 at xHigh/16,384 first. Score every task, reporting usable-answer grammatical accuracy separately from refusals, invalid outputs, truncations, and infrastructure failures. Audit systematic disagreements before interpreting hardness. Pair Astra on the same frozen pilot only when Opus results make that useful. The target is the stronger tested reference model's accuracy.

At 80%, a 120-question pilot has independent-Bernoulli SE about 3.65 percentage points, before family dependence. It cannot establish one-point precision or a final 79–81% target. A 1,000-question release has nominal SE about 1.26 points at 80%; at least 1,601 independent questions are needed for SE strictly below one point, and family dependence can require more. Report family-aware uncertainty and costs when results exist.

## Reproduction

The frozen artifacts are `pilot-01.questions.json`, `pilot-01.cells.json`, `pilot-01.manifest.json`, `pilot-01.audit.json`, `source-audit-01.json`, and `supply-01.json`. Their hashes, seed, dictionary/split identities, and generator paths are in the manifest. The generator refuses to overwrite frozen pilot membership.

Run `.venv/bin/python misc/vp_4d_pilot.py` in a clean checkout with no existing pilot artifact to reproduce selection, and `.venv/bin/python misc/vp_4d_source_audit.py` to repeat source checks. Full master-test supply is the sum of its disjoint legacy suballocations; no assignments are changed. The coordinator owns submission and the cumulative ledger; the worker scripts are offline only.
