# GPT-6 Luna xHigh — v3

20,000 tasks: 5,000 per family. Same sampled tasks and v3 templates as the Anthropic runs. xHigh reasoning; no tools, web, history, or benchmark output token cap.

Exact-answer accuracy: **66.945%** (13,389/20,000). Answer plus required format: **66.945%**. Provider refusals: **0**.

Recorded cost across all attempts: **$47.574281**. Attempts with unknown final cost: **29**; these are not treated as free. Prices and reserves are in manifest.json.

| Task family | Correct | Exact accuracy | Answer + format |
|---|---:|---:|---:|
| tinanta | 2,584/5,000 | 51.68% | 51.68% |
| taddhitanta | 3,079/5,000 | 61.58% | 61.58% |
| krdanta | 2,939/5,000 | 58.78% | 58.78% |
| subanta | 4,787/5,000 | 95.74% | 95.74% |

The four family JSON files use the compact 13-field schema embedded in manifest.json. The manifest also pins datasets, templates, rates, API settings, code and verification hashes.

The complete original execution is preserved in [the raw archive](../../archives/luna-xhigh-v3.tar.gz). Every archived file was checked against its original hash. Results were independently schema-validated, rescored and checked against journal replay and source ordering.

To audit, extract the archive into a separate directory and run `data/engine/evaluation/run_openai.py verify --folder <extracted-run>`. This uses local journals and makes no API calls.
