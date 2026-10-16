# Archived Opus 5 tiṅanta traces

`tinanta_old.json` is an unchanged copy of
`data/finetune/sft-r1/claude-opus-5.json` from project commit
`e94499639cf58a6518aa99139fab6818e93346d1`.

- 7,851 records covering 4,564 distinct task IDs.
- 32,870,447 bytes.
- SHA-256: `a65b142ebbac86d884c9012c10f75ecdf66a50b3d167808bfcb8951c5bf7d7c5`.
- All records have stored reward 1.0 under the original verifier.
- All completions contain the old `<thinking>` block.

Each record has `id`, `sample`, `prompt`, `completion`, `answer_devanagari`,
`gold_devanagari`, `reward`, `dhatu`, `morphology`, and `meta`. Prompt and
completion are lists of role/content messages. Metadata retains the original
teacher name and `v1/vp_task_eval.txt` prompt provenance.

The `old` suffix is intentional: this is not a v2 answer-only corpus. Preserve
it as an archive. If reused for future training, export a separately named,
reverified dataset and audit overlap with the new benchmark splits. See
[TRAINING.md](../../../TRAINING.md).
