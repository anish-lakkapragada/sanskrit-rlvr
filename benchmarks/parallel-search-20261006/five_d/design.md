# Isolated 5D pilot 01

**Historical specification.** Read the [current research index](current.md) for the three-recipe menu, fresh480-question confirmation, latest audited reference scores, policy09 supply and family-dependent precision limits. The content below preserves the original pilot01 design; its status and release estimates are superseded.

Prepared 2026-10-06 (America/Los_Angeles). This records the original development pilot specification, not a completed benchmark. The subsequent [release feasibility review](release-feasibility-01.md) reports the measured Opus result, prospective grammar exclusions, full master-test supply assessment and current continuation recommendation; it supersedes the pre-evaluation status statements below.

The input is one dictionary dhatu, identified by its citation, gana and traditional meaning, plus exactly five coordinates: lakara, prayoga, purusha, vacana and a fixed derivation recipe. Each task asks for one Devanagari conjugated form. A recipe is one menu value even when its implementation contains several ordered `Sanadi` operations. Prefixes are absent. Pada is never selected or supplied independently; the engine's permitted alternatives are retained.

## Finite recipe menu

The menu is fixed for this pilot. Operations are applied from left to right to the dictionary entry before finite inflection.

| Recipe ID | `Dhatu.with_sanadi` value | Questions | Meaning |
|---|---|---:|---|
| `causative` | `[Ric]` | 10 | Causative |
| `desiderative` | `[san]` | 10 | Desiderative |
| `intensive` | `[yaN]` | 20 | Traditional intensive formation |
| `intensive_luk` | `[yaNluk]` | 20 | Intensive with deletion of yaN |
| `causative_of_intensive` | `[yaN, Ric]` | 30 | Causative of the intensive |
| `desiderative_of_causative_of_intensive` | `[yaN, Ric, san]` | 30 | Desiderative of that causative |

Every question exercises an added recipe; there is no ordinary-conjugation control. Maximum recipe concentration is 25%, and maximum operation-chain length is three. Four recipes are elementary or have one intensive operation; the two nested recipes supply a principled composition challenge without adding another input coordinate.

The intensive's traditional semantic conditions remain part of the operation's definition. Motion roots use the prescribed crooked-motion sense; the listed roots under 3.1.24 use the depreciative sense. These meanings are determined by the lexical entry and the traditional rule, not chosen independently per task. The prompt uses the ordinary grammatical label “intensive.” See the [Kashika on 3.1.22](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.22.htm), [3.1.23](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.23.htm) and [3.1.24](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.24.htm).

## Predeclared distribution and actual supply

The 120 questions use 120 distinct development families. A family retains the existing definition: exact Dhatupatha citation including markers plus gana. This is not a claim of 120 unrelated etymological roots. Class-slot assignments and root selection were fixed without model answers.

| Axis | Pilot distribution |
|---|---|
| Lakara | Lat, Lit, Lut, Lrt, Lot, Lan, VidhiLin, AshirLin, Lun and Lrn: 12 each |
| Prayoga | Kartari 90; Karmani 30; no Bhave |
| Purusha | Prathama, Madhyama and Uttama: 40 each |
| Vacana | Eka, Dvi and Bahu: 40 each |
| Person × number | Each of nine cells has 13 or 14 questions |
| Gana | Bhvadi 48, Adadi 10, Juhotyadi 5, Divadi 12, Svadi 8, Tudadi 16, Rudhadi 6, Tanadi 2, Kryadi 8, Curadi 5 |

The largest root class is 40%; no tense exceeds 10%. The present system contributes 40%, aorist 10%, and benedictive 10%. The pilot is not concentrated in archaic inflection or a single difficult tense. Curadi appears only in the simple causative/desiderative recipes. Scarce Tanadi and Juhotyadi families were assigned to simple recipes first, before root selection, to preserve all ten classes without reusing families.

Karmani occurs only in causal recipes, in Lat, Lan, Lot, VidhiLin, Lut and Lrt. The causal interpretation supplies an object; passive construction does not depend on assuming every unmodified root is transitive. Passive causatives and passives of desideratives have traditional support, while their combination with the nested intensive chain is a compositional inference. See [3.1.26](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.26.htm), [3.4.69](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.4.69.htm) and [Whitney §§1025, 1039 and 1052](https://en.wikisource.org/wiki/Sanskrit_Grammar_(Whitney)/Chapter_XIV).

The development supply probe tested the present active third-person singular of every recipe over all 700 development families. It found 700 eligible families for each simple recipe, 506 for intensive, intensive-luk and intensive-causative, and 437 for intensive-causative-desiderative after the declared filters. These are recipe-specific family counts in one inflection cell, not full Cartesian counts. They establish useful breadth while making no claim about uninspected reserved-test gold. Detailed counts are in `development-supply.json`.

## Grammar and gold audit

The intensive filter requires an engine-normalized consonant-initial base containing one vowel, excludes Curadi and the explicitly unlicensed roch/shobh contexts, and requires nonempty VP derivations. It deliberately leaves aside exceptional vowel-initial intensive licenses. The simple Curadi operations use the dictionary entry's inherent class behavior, followed by the selected recipe; no additional lexical derivative is substituted into the input.

For the two nested recipes, every trace containing 7.4.79, 7.4.80, 7.4.94, 7.4.95 or 8.3.61 is excluded, regardless of scores. These exclusions carry forward unresolved rule-application concerns from the earlier campaign. They do not assert that the rules themselves are invalid. The elementary recipes retain ordinary, unproblematic applications of those rules. Known issues are recorded in `../../iterative-goal-20261006/nested-oracle-review-02.json` and the earlier interaction review.

The pilot also excludes Let, Bhave, more than 64 engine variants, prefixes, extra pada coordinates, zero-result derivations and previously generated equivalent development inputs. No sampling decision uses a model's answer to an individual pilot question.

All 120 questions passed full regeneration, transliteration round-trip, exact coordinate-schema checks, prompt uniqueness and family-split checks under VP 0.4.0. They also passed the coordinator's full validator. Eight source-given control forms matched VP, covering all six recipe shapes plus causal passive and an additional causative-desiderative control. Those controls are separate from paid pilot membership. See `pilot-01.audit.json`, `pilot-01.runner-audit.json` and `pilot-01.source-checks.json`.

Sanadi-derived stems receive dhatu status under [3.1.32](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.32.htm). Classical finite yaN-luk forms are supported explicitly by the [Kashika on 2.4.74](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/2/2.4.74.htm). Nested intensive-to-causative-to-desiderative examples are given by [Whitney §1025](https://en.wikisource.org/wiki/Sanskrit_Grammar_(Whitney)/Chapter_XIV#1025). These sources license the constructions; they do not independently certify every uncommon root, every tense or every accepted engine alternative. Systematic model/oracle disagreements still require adjudication before release. No source-backed control was added to the paid pilot to inflate accuracy.

## Experiment and continuation rule

Evaluate this frozen pilot on Opus 5.5 with xHigh and 16,384 output tokens first. Use the frozen `cartesian-5d-v1` renderer, which extends the established benign dhatu template with one sanadi field. The coordinator owns every paid request and the cumulative ledger.

The initial weights use the earlier composition experiment only as a rough development clue. That experiment included prefixes and had different exclusions; its approximately mid-80% Opus score is not an estimate for this isolated pilot. The present target remains 79–81% for the strongest tested reference model. There is currently no measured isolated-5D score and no claim that this pilot already meets the target.

Report accuracy by the fixed recipe and tense/voice groups, alongside completion, refusal, truncation, invalid-output and infrastructure categories. Treat grammatical disagreement separately from those categories. Audit systematic error patterns before changing the distribution. Prefer adjusting recipe weights across broad tenses to concentrating on one aorist or rare-root subset. Any new distribution gets fresh development questions; final membership must never be filtered by those questions' own model errors.

After the Opus pilot and disagreement audit, pair Astra on the same 120 questions if informative under the shared budget. Astra could be stronger on the nested recipes, so an Opus-only 80% estimate cannot establish the strongest-reference target. Freeze final weights, grammatical exclusions, family allocation and any extension rule before exposing final answers.

## Splits, scale and precision

The existing split remains 700 development, 1,000 test and 462 RL-training families. At pilot preparation, the legacy reserved-test allocation was 500 initial-release and 500 future-version families. The coordinator subsequently authorized aggregate feasibility assessment across the full master test pool without changing that assignment or choosing final membership; the updated release review records this scope. No held-out model answers were inspected. A later training set must use only the existing RL families.

The pilot's 120 questions are below the benchmark minimum of 500 and preferred size of 1,000. Final task and RL membership are not prepared yet. A 1,000-question benchmark at 80% has an independent-binomial SE of about 1.26 percentage points; at least 1,601 independent questions are needed for strictly less than one point. The 120-question pilot has about 3.65-point SE at 80%. Multiple final tasks per family can increase dependence, so final uncertainty must also include a root-family cluster estimate. The 79–81% point-score target and the precision requirement remain separate.

## Reproduction

Generator: `misc/vp_5d_pilot.py`, seed `2026100605`. Source controls: `misc/vp_5d_source_audit.py`. The generator refuses to replace an existing pilot file; use a new isolated output location/version for reproduction. The manifest records the dictionary, family split, shared generator, renderer and task hashes. The audit subcommand regenerates the current pilot without selecting new members.

No worker model calls were made. `experiment-request.json` is a request for coordinator review and budget-gated execution, not spending authorization or a submitted job. `benchmark_ready` remains false.
