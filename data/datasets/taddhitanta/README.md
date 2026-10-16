# Taddhitanta — all VP affixes

The export uses the same **74,193 resolved stem–gender inputs** as subanta,
read from [shared-nominal-stems.json](../../engine/files/shared-nominal-stems.json).
MWlexnorm is the sole lexical source. Each input is tried with **all 175 VP
taddhita affixes**: **12,983,775 requests** in total.

**3,342,776 tasks** were exported. **9,640,999 requests produced no form**;
there were **zero engine errors and zero gold-encoding failures**. All
outcomes are audited. Retained tasks cover **129 affixes**; the other **46**
were attempted for every input and produced no retained tasks. Each input
contributes **41–51 tasks**.

All **12,983,775 requests were rederived** with history logging enabled and
matched the saved outcomes. Task schemas, gold transliteration, hydrated
prompt digests, source ownership, and artifact hashes passed verification.
This is a schema-2 export.

| File | Contents |
| --- | --- |
| [full.json](full.json) | Tasks with all accepted SLP1/Devanagari answer alternatives |
| [manifest.json](manifest.json) | Counts, input/code/template hashes, patched-engine provenance, artifact hashes |
| [suffixes.json](suffixes.json) | All 175 technical affix IDs and their visible forms |
| [bases.json](bases.json) | Shared input IDs, resolved stems, source genders, constructors, MW IDs, and task counts |
| [attempts.json](attempts.json) | Every attempted coordinate, grouped by input and outcome |
| [source_rows.json](source_rows.json) | All 197,652 dictionary rows, associated inputs, exclusions, and task counts |

Both nominal families use one filtered input list. No excluded raw headwords
are added back. Dictionary rows that resolve to the same spelling and gender
are merged by the shared preparation step, retaining all source IDs. Different
source genders stay separate: gender can affect taddhita rules even though
this task does not request a case, number, or output gender.

Gold comes from pinned VP 0.4.0 plus the documented
[nominal-input compatibility patch](../../engine/taddhitanta/nominal-input.patch).
The bridge supplies gender on the base term and removes VP's empty nyap marker
before taddhita rules run, retaining the complete feminine stem and its tags.
It fixes the known `cUqAvat`, `mAyAvin`, and `samIna` reference failures without
hardcoding individual words or changing suffix rules. The manifest identifies
the archive, patch, Rust bridge, dependency lock, and patched engine files.

Records have `id`, `pratipadika`, `morphology`, `gold_slp1`, and
`gold_devanagari`. Task identity is stem + constructor + source gender + affix.
`pratipadika` includes `linga`, the shared `nominal_id`, and contributing MW IDs.
`morphology` contains `taddhita` and `artha: null`: meaning is unrestricted.
The [prompt](../../engine/prompts/v2/vp_taddhitanta.txt) displays the resolved
stem, its source gender and interpretation, and the technical affix. It asks
for a derived stem or complete indeclinable, without case/number endings.

`attempts.json` partitions all 175 affixes for every input into `exported`,
`no_forms`, `invalid_gold_encoding`, and `engine_error`. Empty results do not
become answerable tasks, and they are not proof of linguistic impossibility.
Engine errors prevent publication.

In `source_rows.json`, `input_status` describes the shared lexical preparation.
`exported_tasks` includes tasks shared between dictionary rows;
`new_unique_tasks` assigns each task to its first source row and sums to the
unique dataset size. All 54,947 contributing source rows yield tasks.
Alternative gold forms are accepted answers to one task, not additional tasks.

The [preflight report](../nominal-preflight/report.json) records the targeted
reference checks. Two known VP gaps remain for `pfTu/mfdu + aR` with explicitly
restricted `TasyaBhava`; this export uses unrestricted meaning. Engine-backed
answers are not independent linguistic certification.

The [historical pilot](pilot/README.md) is preserved as an older diagnostic
snapshot. No model calls, sampling, or train/dev/test splits are part of full
generation. See [reproduction commands](../../engine/taddhitanta/README.md).
