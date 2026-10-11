# Runtime snapshot — 2026-10-07

This additive [snapshot](snapshot.json) records the runtime used during the current calibration: Python 3.10.18, Vidyut 0.4.0, NumPy 2.2.6, Anthropic SDK 0.120.0 and OpenAI SDK 3.19.2. It fingerprints 4,259 installed files across nine critical distributions, including the compiled Vidyut engine, and preserves the complete installed version inventory plus hashes of the dictionary, `uv.lock` and `pyproject.toml`.

The Vidyut binary SHA256 is `a001d8479e03335eea3dc57f68660dd47bffb9f6cf5e9482807c28ad13c44e47`. The snapshot SHA256 is `54abbf989ce0b8ceb3c075fa0e5b2364a4b47159f7fce1ae31fa88cf23f8457a`.

This closes a documentation gap between a package version and its actual local bytes. It is not a retroactive proof of the runtime used in older experiments, an installable environment lock, or independent certification of Sanskrit correctness. No running dependency, package, prompt, task or scope policy changed. Credentials, environment variables, installation URLs and model responses were not read.

From the repository root, verify the captured critical files with:

```sh
.venv/bin/python benchmarks/parallel-search-20261006/runtime-20261007-01/verify.py
```

Before a final release is frozen, include the runtime snapshot and verifier in its provenance, check these bytes again, and retain full task regeneration. Any intended environment change needs a new snapshot and regeneration; do not silently update this record. The version inventory describes additional installed packages but the verifier deliberately gates only the nine critical distributions and explicit runtime/input files.
