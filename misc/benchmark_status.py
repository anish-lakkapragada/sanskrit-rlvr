"""Concise, read-only status of the shared full-evaluation run."""
import json
from pathlib import Path

root = Path("/lambda/nfs/sanskrit-serve/grpo-r3-full-20260920")


def tail(path, size=2200):
    if not path.exists():
        return ""
    with path.open("rb") as f:
        f.seek(max(0, path.stat().st_size - size))
        return f.read().decode(errors="replace").replace("\r", "\n")


status = {"model_ready": (root / "model-ready.json").exists(), "workers": [], "total_completed": 0}
if not status["model_ready"]:
    status["setup_tail"] = tail(root / "setup.log").splitlines()[-5:]
for worker in range(4):
    progress = root / "results" / f"samples-{worker}.progress.json"
    record = json.loads(progress.read_text()) if progress.exists() else {"completed": 0}
    record["worker"] = worker
    record["done"] = (root / "results" / f"samples-{worker}.done.json").exists()
    log = tail(root / f"worker-{worker}.log")
    record["log_tail"] = log.splitlines()[-2:]
    status["total_completed"] += record["completed"]
    status["workers"].append(record)
print(json.dumps(status, ensure_ascii=False))
