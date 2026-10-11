#!/usr/bin/env python3
"""Run one evaluation on Lambda, retain NFS outputs, and clean up this GPU.

The credential is read from stdin into memory, never written to the run folder.
Only the exact instance ID supplied at startup can be terminated.
"""
import base64
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request


def atomic(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def main():
    config = json.loads(sys.stdin.readline())
    secret = config.pop("api_key")
    out = Path(config["out"])
    instance_id = config["instance_id"]
    deadline = time.monotonic() + 6 * 3600
    worker = None
    reason = None
    with (out / "worker.log").open("ab", buffering=0) as log:
        worker = subprocess.Popen(["bash", config["script"]], stdin=subprocess.DEVNULL,
                                  stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        atomic(out / "guard.json", {"started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "instance_id": instance_id, "pid": os.getpid(), "worker_pid": worker.pid,
            "hard_deadline_hours": 6, "status": "running"})
        while time.monotonic() < deadline:
            code = worker.poll()
            if code is not None:
                summary = out / "summary.json"
                complete = summary.exists() and json.loads(summary.read_text()).get("complete", False)
                atomic(out / "worker-exit.json", {"exit_code": code, "complete": complete,
                    "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
                if (out / "local-collected.json").exists():
                    reason = "results_copied_to_local_workspace" if complete else "failure_outputs_collected"
                    break
            time.sleep(20)
        if reason is None:
            reason = "six_hour_deadline_outputs_retained_on_nfs"
        if worker.poll() is None:
            os.killpg(worker.pid, signal.SIGTERM)
            try:
                worker.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(worker.pid, signal.SIGKILL)
                worker.wait()
    atomic(out / "cleanup.json", {"requested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "instance_id": instance_id, "reason": reason, "outputs_on_persistent_nfs": True})
    # A network interruption must not strand a billed instance. Retrying this
    # idempotent termination affects only this run's single recorded instance.
    for attempt in range(120):
        try:
            req = urllib.request.Request("https://cloud.lambda.ai/api/v1/instance-operations/terminate",
                headers={"Authorization": "Bearer " + secret, "Content-Type": "application/json", "User-Agent": "curl/8.7.1"},
                data=json.dumps({"instance_ids": [instance_id]}).encode())
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.load(response)
            atomic(out / "termination-receipt.json", result)
            return
        except Exception as exc:
            atomic(out / "cleanup-error.json", {"attempt": attempt + 1, "type": type(exc).__name__,
                  "http_status": getattr(exc, "code", None)})
            time.sleep(30)
    raise SystemExit("Termination retries exhausted; instance ID is recorded in cleanup.json")


if __name__ == "__main__":
    main()
