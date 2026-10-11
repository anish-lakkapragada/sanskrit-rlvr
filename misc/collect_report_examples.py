#!/usr/bin/env python
"""Collect model-behavior examples for the misc/ report via the serving app.

Requires ./serving/serve.sh to be live (localhost:7860 -> tunneled vLLM
servers). Writes misc/report_examples.json: one entry per (prompt, model)
with the rendered prompt, output, and latency. T=0.2, the eval temperature.

Usage: uv run --with httpx python misc/collect_report_examples.py
"""

import asyncio
import json
from pathlib import Path

import httpx

APP = "http://localhost:7860"
OUT = Path(__file__).parent / "report_examples.json"

MODELS = ["base", "tb20m-samayik100", "tb20m-samayik67", "tb20m-samayik0",
          "grpo-r3", "tb20m-samayik100-avg", "tb20m-samayik67-avg", "grpo-r3-avg"]

BATTERY = [
    # (id, template, prompt, max_tokens, what it probes)
    ("chat-foods", "raw", "Name three Indian foods.", 512,
     "general chat request — the canonical silence probe"),
    ("chat-math", "raw", "Please tell me what 2 + 2 is", 512,
     "trivial question, polite phrasing"),
    ("instr-oneword", "raw", "Answer with exactly one word: what color is the sky?", 512,
     "explicit output-format instruction"),
    ("instr-json", "raw", 'Reply with only this JSON object: {"ok": true}', 512,
     "verbatim-echo instruction"),
    ("chat-haiku", "raw", "Write a haiku about rain.", 512,
     "creative request"),
    ("instr-french", "raw", "Translate 'The boy reads a book.' into French.", 512,
     "translation instruction to a DIFFERENT language — silo probe"),
    ("tpl-translation", "translation (v0 eval)", "The boy reads a book.", 1024,
     "the trained translation door"),
    ("tpl-scaffold", "elicitation scaffold", "The boy reads a book.", 1024,
     "explicit derive-first instruction inside the trained format"),
    ("tpl-costume", "drill costume (conjprompt)", "The boy reads a book.", 1024,
     "the trained drill door carrying translation content"),
]


async def main():
    results = []
    async with httpx.AsyncClient(timeout=600) as cli:
        for pid, tpl, prompt, max_tok, note in BATTERY:
            r = await cli.post(f"{APP}/api/generate", json={
                "prompt": prompt, "template": tpl, "temperature": 0.2,
                "max_tokens": max_tok, "models": MODELS})
            d = r.json()
            for res in d["results"]:
                results.append({"probe": pid, "template": tpl, "input": prompt,
                                "note": note, "model": res["model"],
                                "output": res["output"], "seconds": res["seconds"]})
            done = sum(1 for x in results if x["probe"] == pid)
            print(f"[{pid}] {done} models done")
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    print(f"wrote {OUT} ({len(results)} examples)")


if __name__ == "__main__":
    asyncio.run(main())
