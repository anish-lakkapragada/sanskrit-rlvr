#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Refresh all sample dependencies, preserving still-eligible sample IDs."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.tinanta import common as tinanta
from data.engine.krdanta import common as krdanta
from data.engine.subanta import common as subanta
from data.engine.taddhitanta import common as taddhitanta
from data.engine.reports.refresh_nominal_samples import article

SAMPLES = ROOT / "data/engine/prompts/v2/samples"
FAMILIES = {"tinanta": ("Tiṅanta", tinanta), "krdanta": ("Kṛdanta", krdanta),
            "subanta": ("Subanta", subanta), "taddhitanta": ("Taddhitānta", taddhitanta)}


def refresh():
    manifest = json.loads((SAMPLES / "manifest.json").read_text())
    page = (SAMPLES / "samples.html").read_text()
    files, changes = {}, {}
    for family, (label, common) in FAMILIES.items():
        old = manifest["datasets"][family]
        source = ROOT / "data/datasets" / family / "full.json"
        metadata = json.loads(source.with_name("manifest.json").read_text())
        digest = subanta.sha256(source)
        assert digest == metadata["files"]["full.json"]["sha256"]
        template_hash = subanta.sha256(common.TEMPLATE)
        if digest == old["source_sha256"] and template_hash == old["template_sha256"]:
            for sample in old["samples"]:
                assert common.render_task(sample["inputs"]) == (SAMPLES / sample["path"]).read_text()
                assert subanta.sha256(SAMPLES / sample["answer_path"]) == sample["answer_sha256"]
            changes[family] = {"preserved": 5, "replaced": []}
            continue
        total = metadata["counts"].get("full", metadata["counts"].get("all"))
        assert total >= 5 and metadata["generation_complete"]
        seed = f"{manifest['seed']}:{family}:{digest}:eligible-replacements"
        # Ten random candidates guarantee at least five not among the old five.
        replacement_indices = random.Random(seed).sample(range(total), min(total, 10))
        targets = set(replacement_indices)
        old_ids = {s["task_id"] for s in old["samples"]}
        retained, candidates = {}, {}
        observed = 0
        for index, row in enumerate(subanta.iter_array(source)):
            if row["id"] in old_ids:
                retained[row["id"]] = (index, row)
            if index in targets:
                candidates[index] = row
            observed += 1
        assert observed == total
        replacements = iter((i, candidates[i]) for i in replacement_indices if candidates[i]["id"] not in retained)
        selected, replaced = [], []
        for number, previous in enumerate(old["samples"], 1):
            if previous["task_id"] in retained:
                index, row = retained[previous["task_id"]]
            else:
                index, row = next(replacements)
                replaced.append({"sample": number, "old_task_id": previous["task_id"], "new_task_id": row["id"]})
            assert not row.get("warnings") and row["gold_devanagari"]
            prompt = common.render_task(row)
            answer = json.dumps({k: row[k] for k in ("id", "gold_slp1", "gold_devanagari")}, ensure_ascii=False, indent=2) + "\n"
            prefix = f"{family}/{number:02d}"
            files[f"{prefix}/prompt.txt"] = prompt
            files[f"{prefix}/answer.json"] = answer
            inputs = ("dhatu", "morphology") if "dhatu" in row else ("pratipadika", "morphology")
            selected.append({"path": f"{prefix}/prompt.txt", "record_index": index, "task_id": row["id"],
                             "inputs": {k: row[k] for k in inputs}, "warnings": [],
                             "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                             "answer_path": f"{prefix}/answer.json", "answer_sha256": hashlib.sha256(answer.encode()).hexdigest()})
            page, count = re.subn(rf'<article id="{family}-{number:02d}">.*?</article>',
                                 lambda _: article(family, label, number, row["id"], prompt, answer), page, flags=re.S)
            assert count == 1
        manifest["datasets"][family] = {
            **old, "source": str(source.relative_to(ROOT)), "source_sha256": digest,
            "source_records": total, "template": str(common.TEMPLATE.relative_to(ROOT)),
            "template_sha256": template_hash, "engine": metadata["engine"],
            "sampling": "Preserve previously sampled IDs still present; replace removed IDs by seeded uniform draws without replacement.",
            "sampling_seed": seed, "samples": selected,
        }
        changes[family] = {"preserved": 5 - len(replaced), "replaced": replaced}
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    manifest["sampling"] = "Five distinct eligible records per family; dataset entries specify initial sampling and replacement policy."
    manifest["last_refresh"] = changes
    files["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    files["samples.html"] = page
    with tempfile.TemporaryDirectory(prefix=".sample-refresh-", dir=SAMPLES.parent) as tmp:
        for name, text in files.items():
            path = Path(tmp) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        for name in files:
            (Path(tmp) / name).replace(SAMPLES / name)
    print(json.dumps(changes, indent=2))


if __name__ == "__main__":
    refresh()
