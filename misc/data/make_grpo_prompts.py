#!/usr/bin/env python
"""GRPO round-3 prompt set: the 6,018 training tasks minus the 174 tasks whose
Opus traces form the val-morphology eval-loss holdout, so that holdout stays a
true holdout through the RL stage too (GRPO trains on rollouts from prompts,
never on gold traces — but prompt overlap would still weaken the diagnostic).

Asserts the invariants the round depends on: zero task/dhatu overlap with the
669-task vp-eval set, zero task overlap with val-morphology.

Usage:  uv run python misc/data/make_grpo_prompts.py
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SRC = REPO_ROOT / "data" / "finetune" / "task-data" / "finetune.json"
VAL_MORPH = REPO_ROOT / "data" / "data-mixture" / "val-morphology.json"
VP_EVAL = REPO_ROOT / "data" / "data-mixture" / "eval" / "vp-eval.json"
OUT = REPO_ROOT / "data" / "data-mixture" / "grpo-prompts.json"


def main() -> None:
    tasks = json.loads(SRC.read_text())
    held_out = {r["id"] for r in json.loads(VAL_MORPH.read_text())}
    vp = json.loads(VP_EVAL.read_text())
    vp_ids = {t["id"] for t in vp}
    vp_dhatus = {t["dhatu"]["code"] for t in vp}

    kept = [t for t in tasks if t["id"] not in held_out]
    assert len(kept) == len(tasks) - len(held_out), \
        f"expected to drop {len(held_out)}, dropped {len(tasks) - len(kept)}"
    assert not {t["id"] for t in kept} & vp_ids, "task-id leak into vp-eval"
    assert not {t["dhatu"]["code"] for t in kept} & vp_dhatus, "dhatu leak into vp-eval"
    assert not {t["id"] for t in kept} & held_out, "val-morphology task survived the filter"

    with OUT.open("w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=1)
        f.write("\n")

    manifest_path = REPO_ROOT / "data" / "data-mixture" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["grpo-prompts.json"] = {
        "source": str(SRC.relative_to(REPO_ROOT)),
        "tasks": len(kept),
        "excluded_val_morphology_tasks": len(held_out),
        "vp_eval_overlap": {"task_ids": 0, "dhatus": 0},
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print(f"{OUT.relative_to(REPO_ROOT)}: {len(kept)} tasks "
          f"({len(held_out)} val-morphology tasks excluded); manifest updated",
          file=sys.stderr)


if __name__ == "__main__":
    main()
