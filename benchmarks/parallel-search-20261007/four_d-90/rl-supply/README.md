# RL-only supply for the 52/8/40 ordinary-4D mixture

**The current split supports 32,454 distinct public training questions across 369 RL families. The intended 52/8/40 mixture can supply one 1,400-question pass without repeating a question, but 52% of that pass still comes from only nine short-adanta families.** More conjugations or replayed epochs do not add lexical families. This audit makes no difficulty, learning-effect or precision claim.

The main census uses exactly the same source scope as `candidate-1250-source-filtered`: shared policy21, pilot04's local exclusions, and the three prospective predicates for 10.0430+Lun, 10.0466 and 10.0467. Those three entries are all in the test split and remove no RL input. The unresolved 10.0108/10.0481 source clarifications are also test entries. No extra spelling exclusion is silently applied to training.

| Component | Target share | RL families | Unique public tuples | Distinct family + four-coordinate keys |
|---|---:|---:|---:|---:|
| Short-penultimate literal-a-final Curadi, non-Lun | 52% | 9 | 729 | 729 |
| Other literal-a-final Curadi, Lun | 8% | 15 | 135 | 135 |
| Non-Curadi broad conjugation | 40% | 345 | 31,590 | 31,050 |
| Total | 100% | **369** | **32,454** | **31,914** |

A public tuple includes the dictionary citation, class, meaning and exactly lakara/prayoga/purusha/vacana. Dictionary-code duplicates with identical visible inputs and gold are collapsed. The 540 additional broad public tuples relative to family-coordinate keys arise from distinct meanings within existing families; they do not create more families or coordinate combinations. All questions use Kartari, without prefixes, added Sanadi or separately selected pada. The broad pool covers nine non-Curadi classes and all ten tenses; the two other components add Curadi.

The nine short-adanta RL families are `Dvana`, `kala`, `kzipa`, `maha`, `mfga`, `puwa`, `raca`, `stana` and `vyaya` in the stored SLP1 citation convention. Each has nine non-aorist tenses × three persons × three numbers = 81 available public questions. The 15 other-adanta families each contribute the nine Lun person/number combinations. These are mechanically regenerated, source-filtered capacities, not independent full-paradigm certification of these fresh RL entries.

## Concrete metadata curriculum

[curriculum-1400-metadata.json](curriculum-1400-metadata.json) provides a deterministic, train-only ordering of **728 short + 112 other-aorist + 560 broad** questions. Its 56 blocks each contain **13 + 2 + 10** questions, exactly preserving 52/8/40. Selection uses only input hashes and family/tense/class/person/number loads. Broad blocks cover all ten tenses. No model performance enters membership or order.

All 369 available families occur in this pass. Short-family loads are 80–81, other-aorist loads 7–8, and broad-family loads 1–2. The overall maximum is 81 and the family-load sum of squares is 60,718. All 1,400 selected records were fully regenerated and checked by the shared task validator; the metadata retains prompt and full canonical-gold hashes for later regeneration. It does not export prompts, rewards or model answers.

The hard pool is the without-replacement limit: each 25-question block needs 13 short questions, and `floor(729/13)=56`. Thus **1,400 is the largest complete-block pass** at exactly these weights. It leaves 1 short question, 23 other-aorists and **31,030 broad questions** unused. Expanding an epoch at the same mixture requires replaying short-family forms while drawing more broad examples. This can be a training choice, but must be counted as repetition rather than new data.

There are only **81 short-family × tense pairs**. A design allowing at most one short question per family/tense can sustain only six exact blocks, or **150 total questions**, before repetition of those pairs is unavoidable. Distinct persons and numbers remain valid tasks; they provide a narrower kind of variation than distinct roots.

The curriculum's class proportions follow train-family coverage and balanced loads; they are not asserted to reproduce every class margin of the development or proposed test panel. Its component weights do match. The broad allocation uses 344 Bhvadi, 70 Divadi, 68 Tudadi, 24 Adadi, 20 Kryadi, 16 Svadi, 8 Juhotyadi, 6 Tanadi and 4 Rudhadi questions. All three persons and numbers are balanced within one question per component, and broad tenses each receive 56.

## Separation and leakage limits

The master split remains unchanged at 462 RL-training, 700 development and 1,000 test families, grouped by **exact citation + class**. Every inventory and curriculum family belongs to the declared RL split. Both family overlap and exact public-tuple overlap are zero against the current 200-question development panel and the 1,250-question source-filtered test candidate. Input-only checks against both campaign job directories find zero modern registered-job family or exact-tuple overlap with this RL inventory.

That is not a claim of unseen Sanskrit lexemes. Ignoring class, the RL inventory and test candidate share **10 exact citations**, involving 11 families on each side: **990 available RL questions**, **22 curriculum questions**, and **11 of the 1,250 candidate questions**. For example, `guDa~` occurs as Divadi in RL and Kryadi in the candidate; `kftI~` occurs as Tudadi in RL and Rudhadi in the candidate. The JSON records every such crossing. Against the development panel, two exact citations cross classes, involving four curriculum questions and two development questions. This secondary diagnostic neither changes assignments nor merges roots by speculative stem or semantic equivalence.

The earlier legacy input corpus contains all 369 of these RL families and 340 of their current public tuples. The master split itself states that earlier legacy analysis inspected all families. Existing checkpoints are **not certified split-clean**. A future learner needs a training-data provenance audit across SFT, RL and validation selection; only the declared RL families may enter its training assets. The supply manifest cannot retroactively establish that an existing checkpoint avoided development/test data.

## Spelling sensitivity and readiness

A separate stricter sensitivity removes any task whose canonical gold contains the previously unresolved vowel+rC sequence, where SLP1 `C` denotes ch. It removes **zero** questions from this RL inventory, so the reported main counts and curriculum do not change. This narrow result does not resolve every Sanskrit spelling variant.

The ending-screen's finite 96-item gemination whitelist is not automatically applicable to these different questions. Before reward/export use, preserve all regenerated canonical alternatives and establish a consistent accepted-spelling policy for training and evaluation. Mechanical VP regeneration alone does not certify that every classical alternative is included. The existing source holds and this limitation should travel with exported assets.

Recommended next step is an offline export review of this train-only manifest, with strict split checks and separate public prompts/private gold metadata. If training is later authorized, use the broad inventory for additional coverage while recording deliberate hard-cell replay, rather than presenting a larger replayed curriculum as more independent root coverage. No training, provider calls, ledger changes, split mutations or held-out model-output reads occurred in this audit.

Artifacts: [supply audit](supply-audit.json), [complete training inventory metadata](training-inventory-metadata.json), [curriculum manifest](curriculum-manifest.json), and [reproduction helper](audit_supply.py). The manifest fingerprints the master split, source policies, candidate comparators and all metadata.
