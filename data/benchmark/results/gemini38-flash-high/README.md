# Gemini 3.8 Flash HIGH — v3

20,000 tasks: 5,000 per family. Same sampled tasks and v3 templates as the Anthropic runs. HIGH thinking; no tools, web, history, maxOutputTokens or thinkingBudget parameters. The requested non-streaming v1 endpoint has a documented model maximum of 65,536 output tokens, used for cost reservation; the request leaves output limits at provider defaults.

Exact-answer accuracy: **92.380%** (18,476/20,000). Answer plus required format: **92.365%**. Provider refusals: **0**.

Gross cost before credits across all attempts: **$1133.795684**. Attempts with unknown final cost: **10**; these are not treated as free. Prices and reserves are in manifest.json.

Each result retains the actual provider trafficType and is priced at its returned Standard or Priority PayGo tier. Any routing change is recorded in the manifest; prompts, model, thinking level and output-limit settings stay unchanged.

| Task family | Correct | Exact accuracy | Answer + format |
|---|---:|---:|---:|
| tinanta | 4,511/5,000 | 90.22% | 90.22% |
| taddhitanta | 4,359/5,000 | 87.18% | 87.14% |
| krdanta | 4,690/5,000 | 93.80% | 93.78% |
| subanta | 4,916/5,000 | 98.32% | 98.32% |

The four family JSON files use the compact 13-field schema embedded in manifest.json. The manifest also pins datasets, templates, rates, API settings, code and verification hashes.

The complete original execution is preserved in [the raw archive](../../archives/gemini38-flash-high-v3.tar.gz). Every archived file was checked against its original hash. Results were independently schema-validated, rescored and checked against journal replay and source ordering.

To audit, extract the archive into a separate directory and run `data/engine/evaluation/run_gemini_flash.py verify --folder <extracted-run>`. This uses local journals and makes no API calls.
