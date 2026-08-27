#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Consolidate FLORES-200 English->Sanskrit into one eval JSON.

Downloads the public FLORES-200 tarball (Meta/NLLB distribution), pairs the
line-aligned eng_Latn and san_Deva files from the dev and devtest splits
(professionally translated, n-way parallel), shuffles with a fixed seed, and
writes data/eval/flores-200.json as a flat array of {"en": ..., "sa": ...}
pairs -- the same shape as data/eval/samayik.json.

Usage:  uv run misc/data/fetch_flores_eval.py
"""

import json
import random
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = REPO_ROOT / "data" / "eval" / "flores-200.json"
URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"
SPLITS = ("dev", "devtest")
SEED = 42


def read_lines(tar: tarfile.TarFile, member: str) -> list[str]:
    try:  # members are archived with a leading "./"
        f = tar.extractfile(f"./{member}") or tar.extractfile(member)
    except KeyError:
        f = tar.extractfile(member)
    if f is None:
        sys.exit(f"missing member in tarball: {member}")
    return f.read().decode("utf-8").splitlines()


def main() -> None:
    with tempfile.NamedTemporaryFile(suffix=".tar.gz") as tmp:
        print(f"downloading {URL} ...", file=sys.stderr)
        with urllib.request.urlopen(URL) as resp:
            tmp.write(resp.read())
        tmp.flush()

        pairs, skipped = [], 0
        with tarfile.open(tmp.name) as tar:
            for split in SPLITS:
                en_lines = read_lines(tar, f"flores200_dataset/{split}/eng_Latn.{split}")
                sa_lines = read_lines(tar, f"flores200_dataset/{split}/san_Deva.{split}")
                if len(en_lines) != len(sa_lines):
                    sys.exit(f"{split}: line-count mismatch "
                             f"(en {len(en_lines)} vs sa {len(sa_lines)})")
                n = 0
                for en, sa in zip(en_lines, sa_lines):
                    en, sa = en.strip(), sa.strip()
                    if not en or not sa:
                        skipped += 1
                        continue
                    pairs.append({"en": en, "sa": sa})
                    n += 1
                print(f"{split}: {n} pairs", file=sys.stderr)
        print(f"skipped empty rows: {skipped}", file=sys.stderr)

    random.Random(SEED).shuffle(pairs)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(pairs, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"wrote {len(pairs)} pairs -> {OUT_PATH.relative_to(REPO_ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
