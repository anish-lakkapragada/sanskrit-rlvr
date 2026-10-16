"""Monitor refusals and notify this Mac on cyber refusal or completion; no API calls."""

from collections import Counter
import argparse
import fcntl
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation import run_claude as runner
from data.engine.evaluation.report_claude import finalize
from data.engine.evaluation.watch_astra import notify


def check_refusals(folder):
    label = folder.name
    path = folder / "refusal-monitor.json"
    previous = json.loads(path.read_bytes()) if path.exists() else {}
    refusals, settled = [], 0
    for family in runner.FAMILIES:
        rows = json.loads((folder / f"{family}.json").read_bytes())
        settled += len(rows)
        for row in rows:
            if row["status"] == "refused":
                details = (row.get("error") or {}).get("stop_details") or {}
                refusals.append({"family": family, "task_id": row["task_id"],
                                 "category": details.get("category", "unspecified"),
                                 "request_id": row.get("request_id"),
                                 "response_id": row.get("response_id")})
    cyber = [row for row in refusals if row["category"] == "cyber"]
    notified_at = previous.get("first_cyber_notification_at")
    if cyber and not notified_at:
        first = cyber[0]
        notify(f"{label}: cyber refusal detected",
               f"{len(cyber)} cyber refusal(s) among {settled:,} saved results. "
               f"First: {first['family']} / {first['task_id']}. "
               "Responses are preserved; the benchmark continues without retries.")
        notified_at = runner.base.now()
    report = {"checked_at": runner.base.now(), "settled_results_scanned": settled,
              "total_refusals": len(refusals), "cyber_refusals": len(cyber),
              "categories": dict(Counter(row["category"] for row in refusals)),
              "first_cyber_notification_at": notified_at, "refusals": refusals}
    runner.base.atomic_write(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def watch(folder):
    label = folder.name
    with (folder / "completion-watch.log").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        print(json.dumps({"event": "watcher_started", "at": runner.base.now(), "pid": os.getpid()}), flush=True)
        while True:
            manifest = json.loads((folder / "manifest.json").read_bytes())
            refusals = check_refusals(folder)
            if manifest["status"] == "completed":
                try:
                    report = finalize(folder)
                    if report["settled"] != 20000 or report["unsettled"] or report["not_started"]:
                        raise RuntimeError("Completed run does not contain 20,000 settled tasks")
                    correct = sum(f["strict_correct"] for f in report["families"].values())
                    failures = sum(count for f in report["families"].values() for status, count in f["statuses"].items() if status != "completed")
                    print(json.dumps({"event": "verification_passed", "at": runner.base.now(), "report": report}), flush=True)
                    notify(f"{label} benchmark finished",
                           f"20,000 tasks verified. {correct / 200:.2f}% strict accuracy; ${report['known_cost_usd']:.2f} recorded cost; {report['unknown_cost_attempts']} costs unknown. {refusals['cyber_refusals']} cyber refusals; {failures} total refusals/incomplete/errors. Saved in {label}.")
                except Exception as error:
                    notify(f"{label} needs review", f"Final verification failed: {error}")
                    raise
                return
            execution = manifest["execution"]
            if manifest["status"] == "paused":
                notify(f"{label} benchmark paused", f"{execution.get('progress', {}).get('settled', 0):,} tasks saved. {execution.get('stopped_reason')}")
                return
            if manifest["status"] == "running" and execution.get("pid"):
                try:
                    os.kill(execution["pid"], 0)
                except ProcessLookupError:
                    time.sleep(2)
                    if json.loads((folder / "manifest.json").read_bytes())["status"] == "running":
                        notify(f"{label} benchmark stopped", "Worker exited without a final checkpoint. Inspect journals before resuming.")
                        return
            time.sleep(30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    watch(parser.parse_args().folder)
