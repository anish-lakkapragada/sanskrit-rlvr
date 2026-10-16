# Haiku 5.5 xHigh — v3 results

Completed and verified: **20,000 tasks**, 5,000 per family. Exact-answer accuracy is **61.205%**; accuracy also requiring the requested output format is **61.040%**.

Recorded cost across all attempts: **$30.796706**. Original failed attempts with unknown charges: **7**. Refusals: **0**, including **0 cyber refusals**. All infrastructure retries are finished.

This folder has the same six-file layout as the [Astra reference](../v2/astra-xhigh/). [manifest.json](manifest.json) contains the pinned inputs, v3 prompt texts, model settings, prices, embedded result schema, final summary, verification records and retry history.

| Family | Results | Exact answers correct | Answer + format correct |
| --- | --- | ---: | ---: |
| tinanta | [tinanta.json](tinanta.json) | 2,107 / 5,000 | 2,107 / 5,000 |
| taddhitanta | [taddhitanta.json](taddhitanta.json) | 2,697 / 5,000 | 2,667 / 5,000 |
| krdanta | [krdanta.json](krdanta.json) | 2,645 / 5,000 | 2,645 / 5,000 |
| subanta | [subanta.json](subanta.json) | 4,792 / 5,000 | 4,789 / 5,000 |

Each JSON file preserves the original 5,000 rows, source order and 13-field schema. Output length is `usage.output_tokens`, which already includes hidden thinking. `correct` is exact string membership in the accepted answers; `format_ok` separately checks for exactly one nonempty `<answer>...</answer>` block with only whitespace outside. No spelling or Unicode normalization is applied. Refusals and errors remain in the 20,000-task denominator.

Requests used `claude-haiku-5-5`, adaptive thinking, `xhigh` effort and the full supported `max_tokens: 128000` allowance. There was no smaller benchmark output cap. Each request contained one hydrated v3 user prompt, with no system message, tools, internet access, conversation history or model fallback. Seed 69 applies to the existing benchmark sample.

The four result JSON files are **byte-for-byte unchanged by this cleanup**. Logs, control files, standalone metadata, journals and any runner history were consolidated into the [original-run archive](../../archives/haiku55-xhigh-v3.tar.gz). Every archived file was checked against its original SHA-256 before removal from this folder. The archive also includes the original README, manifest and result files for complete recovery.

Use the embedded schema and result hashes in the manifest to validate this compact export. For full journal replay, extract the archive to a separate directory and use the original runner's offline `verify --folder` command on the extracted `haiku55-xhigh` directory. The execution layout required by the original verifier remains intact in that archive.
