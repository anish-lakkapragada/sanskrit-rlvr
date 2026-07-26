#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Minimal playground for Gemma (text-only) via the Gemini API.

Usage:
  uv run misc/gemma.py                        # interactive chat (multi-turn)
  uv run misc/gemma.py "your prompt here"     # one-shot
  ./misc/gemma.py "your prompt here"          # same, via the shebang
  GEMMA_MODEL=gemma-4-31b-it uv run misc/gemma.py   # the dense 31B instead

NOTE: the Gemini API no longer serves Gemma 3 (as of 2026-07 this key sees
only gemma-4-26b-a4b-it and gemma-4-31b-it). For actual Gemma 3 12B use
OpenRouter (google/gemma-3-12b-it:free) or run it locally (ollama/MLX).

Reads GEMINI_API_KEY from misc/.env (or the environment). Stdlib only.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

MODEL = os.environ.get("GEMMA_MODEL", "gemma-4-26b-a4b-it")
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"


def load_key() -> str:
    if key := os.environ.get("GEMINI_API_KEY"):
        return key
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"")
    sys.exit("GEMINI_API_KEY not found (set it in misc/.env or the environment)")


def generate(contents: list, key: str, temperature: float = 0.7) -> str:
    body = {
        "contents": contents,
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 1024},
    }
    req = urllib.request.Request(
        API_URL.format(model=MODEL, key=key),
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode(errors='replace')}")
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        sys.exit(f"Unexpected response: {json.dumps(data, ensure_ascii=False, indent=2)}")


def main() -> None:
    key = load_key()

    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        print(generate([{"role": "user", "parts": [{"text": prompt}]}], key))
        return

    print(f"[{MODEL}] interactive chat — empty line or Ctrl-D to quit")
    history = []
    while True:
        try:
            user = input("\nyou> ").strip()
        except EOFError:
            break
        if not user:
            break
        history.append({"role": "user", "parts": [{"text": user}]})
        reply = generate(history, key)
        history.append({"role": "model", "parts": [{"text": reply}]})
        print(f"\ngemma> {reply}")


if __name__ == "__main__":
    main()
