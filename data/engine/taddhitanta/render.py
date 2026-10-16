#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Print the fully hydrated prompt for a full-export task ID."""

import argparse
from pathlib import Path
from common import OUTPUT, nominal, render_task

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id", help="For example, taddhitanta:guru:basic:aR")
    parser.add_argument("--dataset", type=Path, default=OUTPUT / "full.json")
    args = parser.parse_args()
    for row in nominal.iter_array(args.dataset):
        if row["id"] == args.id:
            print(render_task(row), end="")
            break
    else:
        parser.error(f"Task ID not found: {args.id}")
