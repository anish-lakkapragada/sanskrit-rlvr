# Gemini 4 Argon HIGH — v3

20,000 tasks: 5,000 per family. Same v3 prompts, sampled tasks and exact-answer scorer as the other evaluations. Project `sanskrit-project-511705`, location `global`, model `gemini-4-argon`.

Requests omit maxOutputTokens and thinkingBudget; thinkingLevel is HIGH. No tools, web or extra instructions. The specified non-streaming v1 endpoint has a provider default of 32,768 output tokens including thinking.

The four family JSON files use the same compact 13-field schema. usage.output_tokens includes candidate and thinking tokens; provider_usage preserves Google's original usageMetadata. cost_usd is gross before promotional credits; the manifest records the estimated 50% promotional credit separately.

ADC access tokens are held only in process memory and refreshed before expiry. Raw journals are archived after verification; the finished directory contains README.md, manifest.json and the four family result files.

On 2026-10-15 UTC, subsequent requests switched from Standard PayGo to Priority PayGo after the user prioritized speed. Request bodies, model, HIGH thinking and omitted output limits are unchanged. Request headers and actual trafficType are retained in journals; cost_usd uses the returned tier, so earlier standard costs remain unchanged. Gross priority rates per million tokens are $7.20 input, $0.36 cached input, and $36 output; promotional credits are separate.
