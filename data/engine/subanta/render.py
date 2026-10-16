#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Stream a dataset to find one ID and print its hydrated prompt without gold."""

import argparse
from pathlib import Path

from common import OUTPUT, iter_array, render_task


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id", help="For example, subanta:deva:basic:Pum:Trtiya:Eka")
    parser.add_argument("--dataset", type=Path, default=OUTPUT / "full.json")
    args = parser.parse_args()
    for row in iter_array(args.dataset):
        if row["id"] == args.id:
            print(render_task(row), end="")
            break
    else:
        parser.error(f"Task ID not found: {args.id}")
