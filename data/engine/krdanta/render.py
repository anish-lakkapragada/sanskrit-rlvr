#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Print the hydrated LLM prompt for one task ID, without its gold answers."""

import argparse
import json
from pathlib import Path

from common import OUTPUT, render_task


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id", help="For example, krdanta:08.0010:kta")
    parser.add_argument("--dataset", type=Path, default=OUTPUT / "full.json")
    args = parser.parse_args()
    rows = json.loads(args.dataset.read_text(encoding="utf-8"))
    row = next((row for row in rows if row["id"] == args.id), None)
    if row is None:
        parser.error(f"Task ID not found: {args.id}")
    print(render_task(row), end="")
