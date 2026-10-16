# Opus 5.5 xHigh — v3 results

Completed and verified: **20,000 tasks**, 5,000 per family. Exact-answer accuracy is **95.740%**; accuracy also requiring the requested output format is **95.740%**.

Recorded cost across all attempts: **$169.077264**. Original failed attempts with unknown charges: **14**. Refusals: **0**, including **0 cyber refusals**. All infrastructure retries are finished.

This folder has the same six-file layout as the [Astra reference](../v2/astra-xhigh/). [manifest.json](manifest.json) contains the pinned inputs, v3 prompt texts, model settings, prices, embedded result schema, final summary, verification records and retry history.

| Family | Results | Exact answers correct | Answer + format correct |
| --- | --- | ---: | ---: |
| tinanta | [tinanta.json](tinanta.json) | 4,890 / 5,000 | 4,890 / 5,000 |
| taddhitanta | [taddhitanta.json](taddhitanta.json) | 4,417 / 5,000 | 4,417 / 5,000 |
| krdanta | [krdanta.json](krdanta.json) | 4,908 / 5,000 | 4,908 / 5,000 |
| subanta | [subanta.json](subanta.json) | 4,933 / 5,000 | 4,933 / 5,000 |

Each JSON file preserves the original 5,000 rows, source order and 13-field schema. Output length is `usage.output_tokens`, which already includes hidden thinking. `correct` is exact string membership in the accepted answers; `format_ok` separately checks for exactly one nonempty `<answer>...</answer>` block with only whitespace outside. No spelling or Unicode normalization is applied. Refusals and errors remain in the 20,000-task denominator.

Requests used `claude-opus-5-5`, adaptive thinking, `xhigh` effort and the full supported `max_tokens: 128000` allowance. There was no smaller benchmark output cap. Each request contained one hydrated v3 user prompt, with no system message, tools, internet access, conversation history or model fallback. Seed 69 applies to the existing benchmark sample.

The four result JSON files are **byte-for-byte unchanged by this cleanup**. Logs, control files, standalone metadata, journals and any runner history were consolidated into the [original-run archive](../../archives/opus55-xhigh-v3.tar.gz). Every archived file was checked against its original SHA-256 before removal from this folder. The archive also includes the original README, manifest and result files for complete recovery.

Use the embedded schema and result hashes in the manifest to validate this compact export. For full journal replay, extract the archive to a separate directory and use the original runner's offline `verify --folder` command on the extracted `opus55-xhigh` directory. The execution layout required by the original verifier remains intact in that archive.
