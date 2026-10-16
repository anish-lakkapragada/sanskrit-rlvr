"""Watch the local Astra run and notify this Mac after offline verification.

Uses the same Python dependencies as run_astra.py. Makes no API calls.
"""

import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation.run_astra import RUN, inspect, now


def notify(title, message):
    # Pass text as arguments, never interpolate it into AppleScript source.
    script = 'on run argv\n display notification (item 2 of argv) with title (item 1 of argv)\nend run'
    result = subprocess.run(["/usr/bin/osascript", "-e", script, title, message],
                            capture_output=True, text=True, timeout=30)
    print(json.dumps({"at": now(), "title": title, "message": message,
                      "notification_command_succeeded": result.returncode == 0,
                      "notification_error": result.stderr.strip() or None}), flush=True)


def watch():
    # Reuse the log as the lock target; a second watcher cannot create duplicates.
    with (RUN / "completion-watch.log").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("A completion watcher is already running", flush=True)
            return
        print(json.dumps({"at": now(), "event": "watcher_started", "pid": os.getpid()}), flush=True)
        while True:
            manifest = json.loads((RUN / "manifest.json").read_bytes())
            state = manifest["status"]
            if state == "completed":
                try:
                    report = inspect(RUN, verify=True)
                    if report["settled"] != 20000 or report["not_started"] or report["unsettled"]:
                        raise RuntimeError("Completed manifest does not have 20,000 settled primary tasks")
                    correct = sum(f["strict_correct"] for f in report["families"].values())
                    failures = sum(count for f in report["families"].values()
                                   for status, count in f["statuses"].items() if status != "completed")
                    message = (f"20,000/20,000 tasks verified. {correct / 200:.2f}% strict accuracy; "
                               f"${report['known_cost_usd']:.2f} recorded cost. "
                               f"{report['unknown_cost_attempts']} costs unknown. "
                               f"{failures} refusals/incomplete/errors. Results are saved in astra-xhigh.")
                    print(json.dumps({"at": now(), "event": "verification_passed", "report": report}), flush=True)
                    notify("Astra xHigh benchmark finished", message)
                except Exception as error:
                    notify("Astra benchmark needs review", f"The run stopped, but verification failed: {error}")
                    raise
                return
            if state == "paused":
                progress = manifest["execution"].get("progress", {})
                reason = manifest["execution"].get("stopped_reason", "Inspect the manifest")
                notify("Astra xHigh benchmark paused",
                       f"{progress.get('settled', 0):,}/20,000 tasks saved. {reason}")
                return
            pid = manifest["execution"].get("pid")
            if state == "running" and pid:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    # Allow a final atomic manifest write during normal shutdown.
                    time.sleep(2)
                    current = json.loads((RUN / "manifest.json").read_bytes())
                    if current["status"] != "running":
                        continue
                    notify("Astra xHigh benchmark stopped", "The worker exited before marking completion. Inspect saved journals before resuming.")
                    return
            time.sleep(30)


if __name__ == "__main__":
    watch()
