# Subanta generation and prompt rendering

Builds [full.json](../../datasets/subanta/full.json) using **MWlexnorm as the
only lexical source** and `vidyut==0.4.0`. It enumerates eight cases (including
the vocative) and three numbers for each supported, resolved stem–gender pair.
There are no model calls, random samples, or automatic train/test splits.

From the repository root:

```bash
uv run --python 3.11 data/engine/subanta/generate.py
uv run --python 3.11 data/engine/subanta/verify.py --rederive
uv run --python 3.11 data/engine/subanta/test_subanta.py
uv run --python 3.11 data/engine/subanta/render.py subanta:deva:basic:Pum:Trtiya:Eka
```

Existing exports are protected. Use `generate.py --overwrite` to regenerate
in place or `--output /path/to/export` to build elsewhere. The verifier accepts
the same `--output`; the renderer accepts `--dataset /path/to/full.json`.
Generation and verification stream the task array to keep memory bounded.

| File | Responsibility |
| --- | --- |
| [common.py](common.py) | Shared-inventory loading, VP requests, prompt hydration, streaming JSON |
| [generate.py](generate.py) | Exhaustive enumeration within the supported scope, gold forms, provenance, and source-row audits |
| [verify.py](verify.py) | All file hashes, task coordinates, schemas, provenance, gold rendering, prompt digest, and row counts; optional complete rederivation |
| [render.py](render.py) | Find a task ID and print its hydrated prompt |
| [test_subanta.py](test_subanta.py) | Feminine stems, irregular forms, alternatives, deduplication, exclusions, prompt isolation, and failed-build protection |

The task adapter reads only
[shared-nominal-stems.json](../files/shared-nominal-stems.json), verifies its
manifest and hashes, and reuses its resolved spellings and source genders.
It does not repeat dictionary normalization. The shared-list generator owns
the MWlexnorm CSV interpretation and exclusions. There are currently 74,193
inputs, so the full grid has 1,780,632 candidate requests.

The current schema-2 full dataset contains all 1,780,632 candidate tasks.
Complete rederivation passed with zero empty results, encoding failures, or
engine errors. The verifier requires schema 2. The old normalizer remains in common.py
for the historical pilot, but full generation and verification use
`load_stems()` and the shared inventory.

For example, `guru, m:f#vI:n` becomes masculine `guru`, feminine `gurvI`, and
neuter `guru`, each with 24 coordinates. The prompt displays the resolved
feminine stem **गुर्वी**; the model does not need to recover it from गुरु.
Ordinary feminine A/I stems use `Pratipadika.nyap`; other supported stems use
`Pratipadika.basic`. The known `lakzmI` exception uses `basic`. Masculine and
neuter genders are never added unless present in the source.

Not every source entry can be represented reliably by a bare VP stem.
Compound boundaries, special lexical/inflection metadata, unsupported stem
classes, uncertain feminine formation, and ambiguous constructors are
excluded with recorded reasons. In particular, plain `mahat` or a participle
such as `pacat` cannot be accepted merely because VP returns a nonempty form.
Feminine root nouns such as `DI` and `SrI` also need more grammatical metadata.
Implicit feminine formation from `-in`/`-an` is outside this adapter's scope;
supported explicit hints are processed. These are coverage limits, not claims
that the excluded Sanskrit entries are invalid.

Every source row has an audit record, including rows contributing no tasks.
Identical normalized requests are stored once, with all contributing MW IDs.
`exported_tasks` counts the tasks associated with a row, including shared
ones; `new_unique_tasks` assigns each shared task to its first source row so
those counts sum to the dataset size. An answer variant does not create an
extra task: all VP alternatives belong in the same gold list.

Gold is sorted unique SLP1 with aligned NFC Devanagari and lossless
transliteration checks. The template uses only the resolved stem, gender,
case, and number. IDs, source metadata, constructor flags, and gold remain
outside the prompt. Conflicting constructors for an identical displayed
stem and gender are excluded. The manifest hashes the code, source, template,
artifacts, and complete ordered sequence of hydrated prompts.

Builds use temporary files and publish the manifest last. Engine exceptions
abort generation instead of silently dropping requests. `--rederive` checks
every candidate again with VP history logging enabled, including any excluded
engine result. This establishes reproducibility against VP, not independent
linguistic certification of every source entry or form.
