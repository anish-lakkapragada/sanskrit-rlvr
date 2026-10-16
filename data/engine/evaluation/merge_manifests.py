"""Consolidate the completed Astra manifest and its pre-retry snapshot."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation import run_astra as base


def merge(folder=base.RUN):
    with (folder / "run.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = folder / "manifest.json"
        old_path = folder / "manifest-before-retries.json"
        current = json.loads(path.read_bytes())
        if current["status"] != "completed" or current["execution"].get("pid"):
            raise RuntimeError("Only consolidate a completed, inactive run")
        history = current.setdefault("manifest_history", [])
        existing = [h for h in history if h["stage"] == "before_retries"]
        if not old_path.exists():
            if len(existing) != 1:
                raise RuntimeError("Pre-retry snapshot is absent and has not been merged")
            return current
        raw = old_path.read_bytes()
        previous = json.loads(raw)
        if previous["run_id"] != current["run_id"]:
            raise RuntimeError("Cannot merge snapshots from different runs")
        digest = hashlib.sha256(raw).hexdigest()
        if existing:
            if len(existing) != 1 or existing[0]["sha256"] != digest or existing[0]["manifest"] != previous:
                raise RuntimeError("Conflicting pre-retry snapshot")
        else:
            history.append({"stage": "before_retries", "source_file": old_path.name,
                            "sha256": digest, "merged_at": base.now(), "manifest": previous})
        base.atomic_write(path, json.dumps(current, ensure_ascii=False, indent=2) + "\n")
        saved = json.loads(path.read_bytes())
        assert saved == current and saved["manifest_history"][-1]["manifest"] == previous
        old_path.unlink()
        descriptor = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return current


if __name__ == "__main__":
    manifest = merge()
    # Selected result files can be verified even after historical journals have
    # been removed from a checkout; never claim to replay absent journals.
    from data.engine.evaluation.scaffold_astra import schema
    validator = base.Draft202012Validator(schema())
    count = 0
    for entry in manifest["tasks"]:
        base.verify_descriptor(entry["dataset"])
        tasks = json.loads((ROOT / entry["dataset"]["path"]).read_bytes())
        rows = json.loads((base.RUN / entry["result_file"]).read_bytes())
        validator.validate(rows)
        assert len(rows) == len(tasks) == 5000
        for row, task in zip(rows, tasks):
            assert row["task_id"] == task["id"]
            score = base.score_output(row["output_text"], task["gold_devanagari"], row["status"])
            assert all(row[k] == v for k, v in score.items())
        count += len(rows)
    print(json.dumps({"merged": True, "verified_selected_rows": count,
                      "historical_journals_present": (base.RUN / "journals").exists()}))
