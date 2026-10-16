# GPT-6 Sol xHigh — v3

20,000 tasks: 5,000 per family. Same sampled tasks and v3 templates as the Anthropic runs. xHigh reasoning; no tools, web, history, or benchmark output token cap.

Exact-answer accuracy: **84.655%** (16,931/20,000). Answer plus required format: **84.655%**. Provider refusals: **0**.

Recorded cost across all attempts: **$451.111834**. Attempts with unknown final cost: **46**; these are not treated as free. Prices and reserves are in manifest.json.

| Task family | Correct | Exact accuracy | Answer + format |
|---|---:|---:|---:|
| tinanta | 3,964/5,000 | 79.28% | 79.28% |
| taddhitanta | 3,956/5,000 | 79.12% | 79.12% |
| krdanta | 4,113/5,000 | 82.26% | 82.26% |
| subanta | 4,898/5,000 | 97.96% | 97.96% |

The four family JSON files use the compact 13-field schema embedded in manifest.json. The manifest also pins datasets, templates, rates, API settings, code and verification hashes.

The complete original execution is preserved in [the raw archive](../../archives/sol-xhigh-v3.tar.gz). Every archived file was checked against its original hash. Results were independently schema-validated, rescored and checked against journal replay and source ordering.

To audit, extract the archive into a separate directory and run `data/engine/evaluation/run_openai.py verify --folder <extracted-run>`. This uses local journals and makes no API calls.
