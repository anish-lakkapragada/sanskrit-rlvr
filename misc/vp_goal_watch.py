"""Collect already submitted iterative-goal batches; never create paid requests."""
import fcntl
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import vp_goal as c, vp_goal_analyze as analysis, oai_batch_eval as io


def refresh_report():
    # Scope audits can change while a batch is running. A fresh interpreter
    # prevents a long-lived collector from applying stale imported predicates.
    subprocess.run([sys.executable, str(ROOT / 'misc/vp_campaign_watch.py'),
                    '--refresh-only'], cwd=ROOT, check=True, timeout=60)


def watch():
    with (c.OUT / "collector.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        io.atomic_json(c.OUT / "collector.json", {"pid": os.getpid(), "started_at": io.now(),
                       "mode": "collect existing batches; idle between research rounds; no paid submission or retry"})
        deadline = time.monotonic() + 26 * 3600
        while time.monotonic() < deadline:
            jobs = [j for j in c.load()["jobs"].values() if j["batch_id"] and not j.get("collected_at")]
            if not jobs:
                refresh_report()
                time.sleep(30)
                continue
            for job in jobs:
                try:
                    result = c.collect(job["id"])
                    if result.get("collected_at"):
                        analysis.analyze()
                except Exception as exc:
                    print(f"Collection failed for {job['id']}: {type(exc).__name__}; no paid retry", flush=True)
            refresh_report()
            time.sleep(30)
        refresh_report()
        io.atomic_json(c.OUT / "collector.json", {"pid": os.getpid(), "stopped_at": io.now(),
                       "mode": "collect existing batches only; no paid submission or retry"})


if __name__ == "__main__":
    watch()
