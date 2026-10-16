"""Re-hash hydrated prompts after template edits without changing dataset rows.

uv run --with vidyut==0.4.0 python data/engine/reports/refresh_prompt_metadata.py
"""
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
FAMILIES = ("tinanta", "krdanta", "subanta", "taddhitanta")


def refresh(family):
    common = importlib.import_module(f"data.engine.{family}.common")
    folder = ROOT / "data/datasets" / family
    metadata = folder / "manifest.json"
    manifest = json.loads(metadata.read_text())
    source_hash, prompt_hash = hashlib.sha256(), hashlib.sha256()
    count = 0
    for raw in (folder / "full.json").open("rb"):
        source_hash.update(raw)
        line = raw.strip()
        if line in (b"[", b"]", b""):
            continue
        row = json.loads(line.removesuffix(b","))
        prompt = common.render_task(row)
        prompt_hash.update((json.dumps([row["id"], prompt], ensure_ascii=False, separators=(",", ":")) + "\n").encode())
        count += 1
    assert source_hash.hexdigest() == manifest["files"]["full.json"]["sha256"]
    assert count == manifest["counts"]["full"]
    manifest["prompt"].update(sha256=hashlib.sha256(common.TEMPLATE.read_bytes()).hexdigest(),
                              rendered_sequence_sha256=prompt_hash.hexdigest())
    manifest["prompt"]["metadata_refreshed_at"] = datetime.now(timezone.utc).isoformat()
    temp = metadata.with_suffix(".json.tmp")
    temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    temp.replace(metadata)
    print(f"{family}: refreshed {count:,} prompt hashes; dataset unchanged", flush=True)


if __name__ == "__main__":
    with ProcessPoolExecutor(max_workers=4) as pool:
        list(pool.map(refresh, FAMILIES))
