# How VP-Bench tasks A, B, and C were generated

**Release documented:** VP-Bench ABC-400, version 1, 10 October 2026.  
**Size:** 400 tasks per family; 1,200 tasks in total.

This document describes the implemented generator and the released answer keys. The benchmark uses Vidyut-Prakriya (VP) to generate grammatical forms, search for compatible analyses, and build reference answers. Fixed code renders the prompts and selects the released items. No LLM is called to write, select, review, or grade individual items in this pipeline.

## 1. What each task measures

| Family | What the model receives | What it must return | Reference-answer construction |
| --- | --- | --- | --- |
| **A — Complete finite-verb analysis** | An isolated conjugated verb form | Every distinct root–lakāra–person–number–pada analysis in the stated scope | Enumerate finite forms across the dictionary and collect every matching analysis |
| **B — Deverbal nominal to finite verb** | An inflected deverbal nominal, its nominal features, and requested finite-verb features | One compatible finite verb form | Find all compatible source derivations, then generate and union their target forms |
| **C — Meaning to taddhita derivative** | A nominal base and a requested meaning; no suffix | One derived nominal stem expressing that meaning | Try every taddhita suffix under that meaning and collect the licensed outputs, with one documented global guard |

The intended solver uses its own knowledge, without tools, code, files, search, or other agents. VP is used by the **benchmark generator and grader**, not by the evaluated model. A no-tools instruction in the prompt must also be enforced by the evaluation harness.

## 2. Shared deterministic infrastructure

The release pins:

- **VP source commit:** `8da2f90bee3ce1c07505fa432fc3729e3f7e02ea` in [ambuda-org/vidyut](https://github.com/ambuda-org/vidyut).
- **Python package:** `vidyut==0.4.0`, used for transliteration and earlier candidate generation.
- **Release selection seed:** `vp-abc-400-v1-2026-10-10`.
- **Inputs:** bundled candidate requests, dictionary data, root-identity groups, semantic templates, and engine results.

Selection and ordering use SHA-256 with fixed inputs. They do not read model responses, error labels, or accuracy scores. The task definitions, quotas, exclusions, and prompt templates are fixed design choices; “deterministic” does not mean that no one designed the benchmark.

A and B reuse frozen candidate pools from earlier deterministic generation work. The release rebuilds their answer keys over the broader declared search scope before choosing the final questions. C draws supported base–meaning pairs from positive upstream tests.

### Root uniqueness

Dictionary entries are grouped conservatively when they share marker-free root aliases. The dictionary contains **2,229 entries**, organized into **1,532 root-identity groups**.

For A and B, uniqueness covers **all compatible roots of an item**, not just the root originally used to generate it. Once an item is selected, every compatible root group is reserved and cannot appear in another item in that family.

Uniqueness is **within each family**: A and B may overlap with each other. C uses nominal bases rather than dhātus, so its corresponding constraint is one task per nominal-base identity.

## 3. Task A: complete finite-verb analysis

### The question

The model sees a finite verb form in Devanagari and IAST. It must return all distinct tuples:

```text
(root, lakara, person, number, pada)
```

The root and grammatical coordinates are hidden. Person uses English numbering: 1 = speaker, 2 = addressee, 3 = third person. Pada is `P` for parasmaipada or `A` for ātmanepada.

### Generation scope

The hidden search includes:

| Dimension | Included values |
| --- | --- |
| Underlying formation | Ordinary, causative (ṇic), desiderative (san), intensive (yaṅ), intensive with yaṅ deleted (yaṅ-luk) |
| Lakāra | `Lat`, `Lit`, `Lut`, `Lrt`, `Lot`, `Lan`, `VidhiLin`, `AshirLin`, `Lun`, `Lrn` |
| Prayoga | Kartari only |
| Person | First, second, third |
| Number | Singular, dual, plural |
| Pada | Parasmaipada and ātmanepada |

The Vedic subjunctive `Let` is excluded. Dictionary-required prefixes are retained, but arbitrary extra prefixes, further sanādi stacking, and omission of the past augment are outside scope.

### How the questions and keys are produced

1. **Start with 800 fixed candidate forms** from the earlier broad finite-verb pool. Each retains its generating root, formation, and grammatical coordinates.
2. **Enumerate the full bounded search space** using the pinned Rust engine:

   ```text
   2,229 dictionary entries
   × 5 formations
   × 10 lakaras
   × 3 persons
   × 3 numbers
   × 2 padas
   = 2,006,100 finite-derivation requests
   ```

   Kartari is fixed. Requests can produce zero, one, or several forms; this is not a count of distinct words.
3. **Match generated outputs to candidate words**, using the documented orthographic normalization.
4. **Collapse equivalent analyses.** Equivalent dictionary entries and different formation paths are merged when the five scored fields coincide. The formation label is deliberately not part of the requested answer.
5. **Select eight items per generating formation × lakāra cell** in fixed hash order, skipping any overlap with previously reserved root groups.
6. **Render the prompt and complete answer set** with fixed templates.

This gives:

```text
5 formations × 10 lakaras × 8 items = 400 tasks
```

There are **80 items per generating formation** and **40 per generating lakāra**. These quotas describe the path used to generate the question, not every possible interpretation in its answer key.

The 400 items reserve **435 root groups** across all interpretations. **332 items have one scored analysis; 68 have more than one.**

### Example from the release: A0207

**Input:** क्षीणीतात् (*kṣīṇītāt*).

**Complete answer:**

```json
[
  {"root": "क्षी", "lakara": "Lot", "person": 2, "number": "singular", "pada": "P"},
  {"root": "क्षी", "lakara": "Lot", "person": 3, "number": "singular", "pada": "P"}
]
```

Both analyses are required. The primary score is exact-set correctness, so omitting a valid analysis or adding an invalid one makes the item incorrect.

### Why A is not simply the full conjugation Cartesian product

The earlier forward task supplied a root and grammatical coordinates, then asked for one form:

```text
root + lakara + prayoga + person + number → verb form
```

A reverses that direction:

```text
verb form → all compatible roots and grammatical analyses
```

Its answer-key generator does enumerate a Cartesian product within the declared scope. The released benchmark, however, contains **400 selected surface forms**, not one question for every coordinate combination of every root.

The four-enum grid excluding `Let` has `10 × 3 × 3 × 3 = 270` combinations per root. A instead fixes prayoga to kartari, searches five formations and both padas, and hides the root. **Pada and prayoga are separate dimensions.** Releasing the full per-root grid would also repeat each root many times, contrary to the uniqueness goal.

## 4. Task B: inflected deverbal nominal to finite verb

### The question

The model receives:

- An inflected kṛdanta, or deverbal nominal.
- Its kṛt suffix, gender, case, and number.
- The requested finite lakāra, person, and number, with kartari fixed.

The underlying root and formation are hidden. The model must infer a compatible source derivation, preserve its ordinary, causative, or desiderative formation and required prefixes, and produce one requested finite form.

### Generation scope

The source uses **masculine forms**, all eight cases, all three numbers, and seven suffixes:

| VP identifier | Source formation |
| --- | --- |
| `kta` | Past participle |
| `ktavatu` | Past active participle |
| `tfc` | Tṛc agent noun |
| `anIyar` | Gerundive |
| `tavyat` | Gerundive |
| `Satf` | Śatṛ present active participle |
| `SAnac` | Śānac present middle participle, kartari |

The target covers the same ten classical lakāras used in A, all three persons, and all three numbers. Any grammatically permitted target pada or optional variant is accepted.

### How the questions and keys are produced

1. **Start with 840 fixed paired requests**, each containing a nominal request and a finite request for the same underlying verb. The original pool was balanced across formations, suffixes, cases, nominal numbers, and target lakāras.
2. **Require nonempty, agreeing outputs.** At pool construction, both nominal and finite output sets had to agree exactly between Python VP 0.4.0 and the pinned Rust engine.
3. **Orient every candidate as nominal → finite.** If several nominal variants exist, choose the displayed source by a fixed hash.
4. **Search all dictionary entries and all three formations** at the source’s specified suffix, gender, case, and number. Retain every derivation that reproduces the displayed nominal.
5. **Generate the target for every compatible source analysis.** Union their valid finite forms, including permitted padas and optional variants.
6. **Select 40 items per target lakāra**, cycling through the ten lakāras in round-robin order. Candidates within each stratum are hash-ordered. Skip candidates whose possible source roots overlap roots already reserved.
7. **Render the prompt and accepted-answer set.** Source readings that produce no target still count when reserving roots.

The result is **400 tasks**, reserving **453 source root groups**. The selected generating paths comprise **141 ordinary, 125 causative, and 134 desiderative** items. All seven suffixes, eight cases, and three nominal numbers remain represented; those dimensions are not exactly balanced in the final subset.

### Handling ambiguous sources fairly

The key is not limited to the root originally used to construct a candidate. A target from **any compatible source analysis** is accepted.

This matters in the released data: **53 items have multiple underlying root groups**, and **109 receive additional accepted outputs beyond the original generating path**.

### Deterministic consistency guard

For `kta`, `anIyar`, `tavyat`, and `SAnac`, when all generated stems are regular a-stems, the pipeline compares:

- VP’s nested derivation-plus-inflection result.
- Separate inflection of the generated stems.

If the normalized sets disagree, that derivation path is excluded. The check applies both during candidate construction and during inverse source analysis. It detects a class of composition inconsistencies; agreement does not independently establish linguistic correctness.

### Example from the release: B0072

**Source:** स्तृतान् (*stṛtān*).  
**Source features:** kta; masculine; accusative plural.  
**Target:** optative (`VidhiLin`); kartari; second person plural.

One accepted response is:

```xml
<answer>स्तृणुयात</answer>
```

**स्तृण्वीध्वम्** (*stṛṇvīdhvam*) is also accepted. The model needs to give only one valid target.

## 5. Task C: derive a taddhita stem from its meaning

### The question

The model sees a nominal base and a requested semantic relation. It must choose an appropriate taddhita suffix and return the resulting nominal stem, without a case ending.

The suffix is hidden. Thus the task includes choosing the derivation from its meaning, as well as producing its surface form.

### Choosing supported base–meaning pairs

Candidates come from positive assertions in VP’s upstream test corpus. An assertion is eligible only when it:

- Is a passing, nonempty `Taddhitanta` derivation.
- Specifies an explicit semantic category (`artha`).
- Uses a basic nominal base.
- Has no `require` output filter.
- Uses classical, unaccented settings, with NLP mode off and no forced optional-rule choices.
- Does not use an indeclinable base.

Five whole semantic categories are excluded because they fall outside this nominal-stem task:

| Category | Reason |
| --- | --- |
| `Sheshe` | Unspecified miscellaneous meaning |
| `DigDeshaKala` | Adverbial direction, place, or time |
| `KriyaAbhyavrttiGanana` | Adverbial repetition count |
| `PrakaraVacane` | Adverbial manner |
| `AbhutaTadbhava` | Formation requiring combination with a verb |

After these filters, there are **672 eligible nominal-base identities**. The generator hash-orders those identities and takes 400. For each selected base, it hash-selects one supported combination of base flags and semantic category.

The resulting **400 distinct bases span 99 semantic categories**. Meanings are not uniformly balanced. The upstream tests determine which vocabulary and semantic combinations are available.

### Building the answer key

For each selected base–meaning pair:

1. Enumerate **all 175 VP taddhita suffix values**, preserving the exact base flags and semantic category.
2. Collect every successful derived stem.
3. Apply the global `bahuc` exclusion described below.
4. Union and deduplicate the surviving stems.
5. Check that the source assertion’s expected forms survive in the corresponding suffix-specific answer set.
6. Render the meaning using a **fixed category-to-English glossary**, then insert it and the base into the prompt template.

The original test suffix is therefore not the only possible accepted suffix. The release stores the full suffix-to-answer mapping and the source-test provenance.

### Global semantic guard for bahuc

At the pinned commit, `taddhita/utils.rs::try_prepend` lacks the explicit semantic guard present in `try_add_with`. Consequently, the unconditional `bahuc` path at rule 5.3.68 can produce a `bahu + base` output for unrelated requested meanings.

The generator still enumerates all 175 suffixes, then **excludes bahuc from every C answer key**. This is a single deterministic rule applied to the whole family, not per-item answer editing or selection based on model errors. Raw outputs and excluded paths remain in the audit data; the upstream source is unmodified.

After this guard, **306 items have one accepted surface stem and 94 have multiple stems**. Separately, 111 items allow multiple suffixes; distinct suffixes can converge on the same surface stem.

### Example from the release: C0026

**Base:** अश्व (*aśva*).  
**Requested meaning:** “A distance that X can travel in one day.”

**Accepted response:**

```xml
<answer>आश्वीन</answer>
```

The stored semantic category is `EkahaGama`; the accepted suffix path is `KaY`. Neither identifier is required in the model’s answer.

## 6. Grading, verification, and limits

### Deterministic grading

A uses exact equality between the predicted and reference sets of analyses. Its grader also reports tuple precision, recall, and F1.

B and C accept **any one member** of their reference-answer sets. The single displayed `answer` is an example, not an exclusive key.

The grader accepts Devanagari, IAST, SLP1, and Harvard-Kyoto. It preserves vowel length while normalizing specified spelling variants, including anusvāra versus homorganic nasals. Finite forms also allow documented final-stop and periphrastic-spacing normalization. C’s underlying stem-final consonants are not automatically devoiced.

### Checks recorded for this release

- Exactly 400 tasks per family, with unique prompts and nonempty keys.
- Root-reservation checks for A/B and base-identity uniqueness for C.
- **9,744 reference-answer grading checks** and **1,600 negative controls**.
- Byte-identical outputs on repeat builds.
- Fresh engine execution from the bundled source snapshot matching all **800 A**, **840 B**, and **400 C** candidate records.

These are generation and software-verification results, **not model trials**.

### What the release does and does not establish

The questions and keys can be reproduced without per-item agent processing or review. Answer completeness is bounded by the pinned dictionary, supported formations, settings, normalization, and documented guards.

The pipeline does not independently certify all Sanskrit judgments. C reflects upstream test coverage rather than corpus frequency. Some A/B roots overlap earlier exploratory pilots, so this release is not a wholly untouched holdout.

**No Astra or Opus evaluation of these 1,200 released items is recorded as completed.** Their generation does not establish an accuracy below 70%, 80%, or 85%.

## 7. Reproducing the release

Inside the extracted `VP-Bench-ABC-400` directory, rebuild prompts and keys from the bundled inputs and cached engine results:

```bash
python -m pip install vidyut==0.4.0
python scripts/build.py
python scripts/verify.py
```

To recompute the engine results from the bundled pinned source first:

```bash
python scripts/run_oracles.py
python scripts/build.py
python scripts/verify.py
```

The second route requires Rust/Cargo. Cargo may download dependencies; it makes no model calls. Use `--offline` with the oracle runner when dependencies are already cached.

| Packaged file or directory | Role |
| --- | --- |
| `specification.json` | Frozen scope, selection seed, and exclusions |
| `scripts/build.py` | Final selection, prompt rendering, and key assembly |
| `scripts/meaning_glossary.txt` | Fixed English templates for C’s semantic categories |
| `rust/global_analysis.rs` | A’s exhaustive finite-form enumeration |
| `rust/abc_conversion.rs` | B’s source inversion and target generation |
| `rust/abc_taddhita.rs` | C’s suffix enumeration |
| `inputs/` and `oracle/` | Frozen candidate inputs and complete candidate engine results |
| `provenance/` | Historical candidate-pool construction code |
| `coverage.json` and `verification.json` | Released counts and recorded checks |
| `*_tasks_with_answers.jsonl` | Prompts, answer sets, and provenance |
| `*_prompts_only.jsonl` | Solver-facing IDs and prompts only |

The supported self-contained rebuild starts from the bundled fixed candidate inputs. Historical scripts under `provenance/` document how those pools were assembled but may assume the original project layout.

