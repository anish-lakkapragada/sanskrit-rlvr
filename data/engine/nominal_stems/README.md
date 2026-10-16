# Shared nominal stems

The first step for both nominal task families is:

**MWlexnorm dictionary rows → explicit stems with genders → merge duplicates → keep supported VP representations.**

[shared-nominal-stems.json](../files/shared-nominal-stems.json) contains one
record per resolved stem spelling and gender. For example, `guru, m:f#vI:n`
produces masculine `guru`, feminine `gurvI`, and neuter `guru`. Another
masculine `guru` dictionary entry adds provenance to the existing record.

```json
{
  "id": "nominal:gurvI:feminine",
  "stem": "gurvI",
  "stem_devanagari": "गुर्वी",
  "gender": "feminine",
  "sources": [
    {
      "source_line": 48363,
      "mw_id": "65987",
      "headword": "guru",
      "compound_headword": "guru",
      "lexnorm": "m:f#vI:n",
      "descriptor": "f#vI",
      "resolution": "explicit_hint"
    }
  ]
}
```

`stem` uses SLP1. The Devanagari spelling is NFC-normalized and checked by
transliterating back to SLP1. Gender is always one of `masculine`, `feminine`,
or `neuter`, taken from the source. All original source fields, the exact
gender descriptor, and the spelling-resolution rule survive deduplication.

The shared file is filtered for the current VP 0.4.0 basic/nyap adapter.
[vp_support.py](vp_support.py) checks source interpretation and reviewed stem
classes before instantiating every retained stem in VP. It verifies the stored
spelling, nyap/indeclinable flags, and the gender's VP enum mapping. VP accepts
arbitrary stem strings, so constructor success alone is not sufficient.

The filter removes source-marked compounds, extended spelling notation that
needs interpretation, special lexical metadata, ambiguous feminine classes,
and unsupported stem classes. Examples include `trayImaya` recorded as
`trayI-maya`, `mahat`, and the feminine root nouns `DI` and `SrI`.
The representation classes follow the existing reviewed subanta adapter:
ordinary a/i/u/r stems, resolved feminine long-vowel stems, polysyllabic
masculine A stems, masculine/neuter an/in stems, supported as/is/us stems,
and go/nau. The known `lakzmI` exception uses `basic`; supported feminine
A/I stems use `nyap`.

Every contributing source interpretation must pass. If a merged row has
both a simple and an unsupported compound analysis, the whole row is removed.
Retained JSON rows are unchanged; all removed rows and their reasons are saved
in `shared-nominal-stems.vp-exclusions.json`. This means future regeneration
reapplies the filter rather than restoring the larger candidate list.

This establishes the current adapter's supported representation scope. It
does not independently certify every Sanskrit entry or guarantee every
taddhita affix. The [task preflight](preflight.py) checks gender handling and the known feminine
constructor discrepancies against the [taddhitanta adapter](../taddhitanta/README.md).
Two explicit-meaning coverage gaps remain documented in its report. The filter does not enumerate questions,
derive forms, or regenerate either task dataset.

The supported lexical rules resolve the common explicit feminine hints,
implicit feminine `a → A`, and neuter final long-vowel
shortening. They follow the pinned
[MWlexnorm explanation](../files/mw-lexnorm/README.upstream.md) and
[stem-model code](https://github.com/funderburkjim/MWlexnorm/blob/34e51125583b1f5026d44e6ef1e44d2a88b73670/step1b/stemmodel.py).
Unknown hints and unresolved feminine formations are recorded rather than
guessed. In particular, bare feminine descriptors on `-n`, `-at` (including
`-mat/-vat`), `-vas`, `-yas`, or `-aYc` do not establish a resolved feminine
stem in this first version. The spelling `-vat` alone does not establish an
adjective: `saMvat` has multiple dictionary senses. Explicit supported hints
can still resolve these endings. Special `LEXID`/`INFLECTID` entries and indeclinables are also recorded
in the audit. Supporting them requires additional lexical interpretation.
An unresolved feminine descriptor does not remove a resolved masculine or
neuter descriptor from the same source row.

The sole lexical input is the existing, checksum-pinned
[MWlexnorm CSV](../files/mw-lexnorm/nominal-entries.csv).
Vidyut 0.4.0 is used for transliteration and constructor checks. No source downloads or model
calls occur during generation. Both task generators now consume this list through [inventory.py](inventory.py).
Both full datasets have been regenerated from this list and completely
rederived: 1,780,632 subanta tasks and 3,342,776 taddhitanta tasks. See the
[validation summary](../../datasets/nominal-preflight/full-regeneration.json).

From the repository root:

```sh
uv run --python 3.11 data/engine/nominal_stems/generate.py
uv run --python 3.11 data/engine/nominal_stems/generate.py --check
uv run --python 3.11 data/engine/nominal_stems/test_nominal_stems.py
uv run --python 3.11 data/engine/nominal_stems/preflight.py
```

Existing exports are protected. Use `--overwrite` to regenerate, or
`--output-dir PATH` to write the four artifacts elsewhere. `--check`
rebuilds and compares all artifacts without changing them.

| File in `data/engine/files` | Contents |
| --- | --- |
| `shared-nominal-stems.json` | Deduplicated stem–gender list with all source analyses |
| `shared-nominal-stems.audit.json` | Every original CSV row, its resolved stem IDs, and any excluded descriptors/reasons |
| `shared-nominal-stems.vp-exclusions.json` | Every resolved stem–gender row removed by the VP representation filter, with full provenance and reasons |
| `shared-nominal-stems.manifest.json` | Counts, normalization policy, source/code hashes, and artifact hashes |

JSON arrays use one complete record per line for streaming reads. Each source
descriptor is accounted for exactly once as resolved or excluded. Counts of
excluded descriptors can exceed counts of excluded rows because a row can
contain several descriptors. The manifest records source-row status separately.
VP removal reasons can overlap; `removed_pairs` counts each removed row once.
Source attribution and licensing information remain in the
[source documentation](../files/README.md#mwlexnorm-dictionary-metadata-with-feminine-hints).
