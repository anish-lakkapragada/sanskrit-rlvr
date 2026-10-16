# Gemini 3.8 Flash HIGH — v3

20,000 tasks: 5,000 per family. Same v3 prompts, sampled tasks and exact-answer scorer as the other evaluations. Project `sanskrit-project-511705`, location `global`, model `gemini-3.8-flash`.

Requests omit maxOutputTokens and thinkingBudget; thinkingLevel is HIGH. No tools, web or extra instructions. The specified non-streaming v1 endpoint has a documented model maximum of 65,536 output tokens, used for cost reservation; the request leaves output limits at provider defaults.

The four family JSON files use the same compact 13-field schema. usage.output_tokens includes candidate and thinking tokens; provider_usage preserves Google's original usageMetadata. cost_usd is gross before promotional credits; the manifest records the estimated 50% promotional credit separately.

ADC access tokens are held only in process memory and refreshed before expiry. Raw journals are archived after verification; the finished directory contains README.md, manifest.json and the four family result files.
