# GPT-6 Astra xHigh — v3

20,000 tasks: 5,000 per family. Same sampled tasks and v3 templates as the Anthropic runs. xHigh reasoning; no tools, web, history, or benchmark output token cap.

Exact-answer accuracy: **93.455%** (18,691/20,000). Answer plus required format: **93.455%**. Provider refusals: **0**.

Recorded cost across all attempts: **$1277.791270**. Attempts with unknown final cost: **56**; these are not treated as free. Prices and reserves are in manifest.json.

| Task family | Correct | Exact accuracy | Answer + format |
|---|---:|---:|---:|
| tinanta | 4,679/5,000 | 93.58% | 93.58% |
| taddhitanta | 4,280/5,000 | 85.60% | 85.60% |
| krdanta | 4,806/5,000 | 96.12% | 96.12% |
| subanta | 4,926/5,000 | 98.52% | 98.52% |

The four family JSON files use the compact 13-field schema embedded in manifest.json. The manifest also pins datasets, templates, rates, API settings, code and verification hashes.

The complete original execution is preserved in [the raw archive](../../archives/astra-xhigh-v3.tar.gz). Every archived file was checked against its original hash. Results were independently schema-validated, rescored and checked against journal replay and source ordering.

To audit, extract the archive into a separate directory and run `data/engine/evaluation/run_openai.py verify --folder <extracted-run>`. This uses local journals and makes no API calls.
