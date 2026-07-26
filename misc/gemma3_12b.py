#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Playground for Gemma 3 12B via OpenRouter (text-only).

Usage:
  uv run misc/gemma3_12b.py                     # interactive chat (multi-turn)
  uv run misc/gemma3_12b.py "your prompt here"  # one-shot
  ./misc/gemma3_12b.py "your prompt here"       # same, via the shebang
  GEMMA_MODEL=google/gemma-3-27b-it uv run misc/gemma3_12b.py ...

Defaults to google/gemma-3-12b-it (the :free pool was retired; as of 2026-07
OpenRouter serves this model paid-only — pennies per call at 12B size).

Reads OPENROUTER_API_KEY from misc/.env (or the environment). Stdlib only.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

MODEL = os.environ.get("GEMMA_MODEL", "google/gemma-3-12b-it")
MAX_TOKENS = int(os.environ.get("GEMMA_MAX_TOKENS", "2048"))
API_URL = "https://openrouter.ai/api/v1/chat/completions"


def load_key() -> str:
    if key := os.environ.get("OPENROUTER_API_KEY"):
        return key
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"")
    sys.exit("OPENROUTER_API_KEY not found (set it in misc/.env or the environment)")


def generate(messages: list, key: str, temperature: float = 0.7) -> str:
    body = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": MAX_TOKENS,
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode(errors='replace')}")
    # OpenRouter can return 200 with an error payload (rate limit, moderation).
    if "error" in data:
        sys.exit(f"API error: {json.dumps(data['error'], ensure_ascii=False)}")
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError):
        sys.exit(f"Unexpected response: {json.dumps(data, ensure_ascii=False, indent=2)}")


def main() -> None:
    key = load_key()

    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        print(generate([{"role": "user", "content": prompt}], key))
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
        history.append({"role": "user", "content": user})
        reply = generate(history, key)
        history.append({"role": "assistant", "content": reply})
        print(f"\ngemma> {reply}")


if __name__ == "__main__":
    main()
