# Gemini 4 Argon HIGH — v3

20,000 tasks: 5,000 per family. Same sampled tasks and v3 templates as the Anthropic runs. HIGH thinking; no tools, web, history, maxOutputTokens or thinkingBudget parameters. The requested non-streaming v1 endpoint has a provider default of 32,768 output tokens including thinking.

Exact-answer accuracy: **95.315%** (19,063/20,000). Answer plus required format: **95.310%**. Provider refusals: **0**.

Gross cost before credits across all attempts: **$666.592818**. Attempts with unknown final cost: **1**; these are not treated as free. Prices and reserves are in manifest.json.

Each result retains the actual provider trafficType and is priced at its returned Standard or Priority PayGo tier. Any routing change is recorded in the manifest; prompts, model, thinking level and output-limit settings stay unchanged.

| Task family | Correct | Exact accuracy | Answer + format |
|---|---:|---:|---:|
| tinanta | 4,708/5,000 | 94.16% | 94.14% |
| taddhitanta | 4,570/5,000 | 91.40% | 91.40% |
| krdanta | 4,850/5,000 | 97.00% | 97.00% |
| subanta | 4,935/5,000 | 98.70% | 98.70% |

The four family JSON files use the compact 13-field schema embedded in manifest.json. The manifest also pins datasets, templates, rates, API settings, code and verification hashes.

The complete original execution is preserved in [the raw archive](../../archives/gemini4-argon-high-v3.tar.gz). Every archived file was checked against its original hash. Results were independently schema-validated, rescored and checked against journal replay and source ordering.

To audit, extract the archive into a separate directory and run `data/engine/evaluation/run_gemini.py verify --folder <extracted-run>`. This uses local journals and makes no API calls.
