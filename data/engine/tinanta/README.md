# Tiṅanta generator

[generate.py](generate.py) considers **601,830 candidates**: 2,229 Dhātupāṭha
entries × 10 tenses/moods × 3 constructions × 3 persons × 3 numbers.
It exports **423,324 eligible tasks** to
[data/datasets/tinanta/](../../datasets/tinanta/README.md).

```bash
uv run --python 3.11 data/engine/tinanta/generate.py --overwrite
uv run --python 3.11 data/engine/tinanta/verify.py --rederive --legacy-commit e94499639cf58a6518aa99139fab6818e93346d1
```

The scripts pin `vidyut==0.4.0` and run locally without model credentials.
Omit `--overwrite` to protect existing exports, or use `--output` for another
directory. Omit `--legacy-commit` when archived Git objects are unavailable.

## Benchmark subset

[export_benchmark.py](export_benchmark.py) samples 5,000 distinct tasks from the
eligible full dataset using seed **69**. Each of the 190 valid grammatical
cells receives 26 tasks, and 60 randomly chosen cells receive one extra task.
Sampling within each cell is uniform and without replacement. The exported
JSON retains each selected source row and all its accepted answers unchanged.

```bash
python3 data/engine/tinanta/export_benchmark.py
```

The output is [data/benchmark/tinanta/tinanta.json](../../benchmark/tinanta/tinanta.json).
Its companion [manifest](../../benchmark/tinanta/tinanta.manifest.json) records cell
counts, hashes, and source indices so the export can be reproduced and audited.

## Eligibility

1. Exclude bhāve (impersonal) coordinates outside third-person singular
   **before** calling VP. This removes 178,320 candidates. Each root has
   90 active + 90 passive + 10 impersonal = **190 eligible coordinates**.
2. Derive all 423,510 remaining candidates. Require nonempty, sorted, unique
   gold sets that round-trip between SLP1 and NFC Devanagari. Empty or malformed
   results are audited; neither occurred in this export. Engine exceptions
   abort publication.
3. Render the actual prompt. If identical prompts have different answer sets,
   exclude every conflicting row. This removes **186 requests** whose dictionary
   entries differ in subclass metadata not expressed by the prompt.

[common.py](common.py) owns these eligibility rules and prompt hydration.
`excluded_tasks.json` records every excluded ID and reason. All exported rows
have `status: "ok"` and `warnings: []`. VP returning a form is not itself a
general grammatical-validity check; these are explicit dataset rules.

## Scope and reproducibility

The source TSV and its hash are pinned. `Data.load_dhatu_entries()` supplies
2,229 usable entries; 30 placeholder rows are excluded. Enumeration uses
dictionary code followed by the axis order recorded in the manifest.
`Let` is outside the classical ten-tense/mood scope.

The official loader supplies subclass metadata and four lexical prefixes:
`02.0012 → AN`, `02.0041 → aDi`, `02.0042 → aDi`, `10.0368 → AN`.
The renderer includes these prefixes when present. No additional prefix or
sanādi combinations are introduced. The engine is classical, without accents
or NLP mode; `dhatu_pada=None` leaves endings to VP, and
`skip_at_agama=False` preserves normal augment behavior.

The verifier checks every candidate against either the export or exclusion
audit, all gold/transliteration pairs, metadata, hashes, counts, and rendered
prompt consistency. `--rederive` recomputes all retained answers with logging
enabled and checks the excluded prompt conflicts. The current run passed:
423,324 records rederived; 4,711 legacy records matched; 1,976 legacy records
were accounted for by the new exclusion rules.

Files are assembled in a temporary directory and published after successful
generation, with the manifest written last. Dataset files and manifest contain
no timestamps or machine-specific paths. After a change, refresh downstream
artifacts with [refresh_samples.py](../reports/refresh_samples.py),
[distribution.py](../reports/distribution.py), and
[token_costs.py](../reports/token_costs.py).
