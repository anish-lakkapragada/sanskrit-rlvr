#!/usr/bin/env python3
"""Copy this Lambda evaluation's outputs locally and verify GPU cleanup."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import abc_local_eval as ev


def main():
    from dotenv import dotenv_values
    import httpx
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    cloud = ev.grade.io.read_json(out / "cloud.json")
    instance = ev.grade.io.read_json(out / "instance.json")
    iid, ip = cloud["instance_ids"][0], instance["ip"]
    values = dotenv_values(ROOT / ".env")
    key = os.environ.get("LAMBDA_API_KEY") or values.get("LAMBDA_API_KEY") or values.get("LAMBDA_CLOUD_API_KEY")
    ssh = ["ssh", "-i", str(Path.home() / ".ssh/id_ed25519"), "-o", "BatchMode=yes",
           "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15",
           "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=2"]
    acknowledged = (out / "local-collected.json").exists()
    remote = cloud["remote_root"] + "/results"
    with httpx.Client(base_url="https://cloud.lambda.ai/api/v1/", headers={"Authorization": "Bearer " + key}, timeout=30) as client:
        while True:
            try:
                response = client.get("instances")
                response.raise_for_status()
                active = [i for i in response.json()["data"] if i["id"] == iid]
                if not active:
                    ev.grade.io.atomic_json(out / "terminated.json", {"verified_at": ev.grade.io.now(), "instance_id": iid,
                        "local_results_verified": acknowledged})
                    print("Evaluation instance is terminated; local results verified:", acknowledged, flush=True)
                    return
                if active[0]["status"] == "terminating":
                    time.sleep(20)
                    continue
                copied = subprocess.run(["rsync", "-az", "--timeout=45", "--exclude=*.tmp", "--exclude=datasets/",
                    "-e", " ".join(ssh), f"ubuntu@{ip}:{remote}/", str(out) + "/"], capture_output=True, text=True, timeout=180)
                if copied.returncode != 0:
                    print("Output sync retry:", copied.stderr[-300:], flush=True)
                    time.sleep(30)
                    continue
                summary = ev.grade.io.read_json(out / "summary.json")
                counts = {label: model["completed_trials"] for label, model in summary["models"].items()}
                print(ev.grade.io.now(), json.dumps(counts), flush=True)
                if summary["complete"]:
                    ev.verify(out)
                    checked = ev.summarize(out)
                    if not checked["complete"] or any(m["completed_trials"] != 4800 for m in checked["models"].values()):
                        raise ValueError("Local results do not cover every trial")
                    marker = {"verified_at": ev.grade.io.now(), "models": 2, "tasks_per_model": 1200,
                              "trials_per_model": 4800, "instance_id": iid,
                              "output_sha256": {label: ev.digest(out / label / "outputs.jsonl") for label in ev.LABELS}}
                    # Ensure the acknowledgement refers to complete, validated
                    # local data before letting the remote guard terminate.
                    ev.grade.io.atomic_json(out / "local-collected.json", marker)
                    ack = subprocess.run(["rsync", "-az", "-e", " ".join(ssh), str(out / "local-collected.json"),
                                          f"ubuntu@{ip}:{remote}/local-collected.json"], capture_output=True, text=True, timeout=60)
                    if ack.returncode:
                        raise RuntimeError("Could not acknowledge saved results")
                    acknowledged = True
                    print("All 9,600 outputs verified locally; cleanup acknowledged", flush=True)
                time.sleep(30)
            except Exception as exc:
                error = {"updated_at": ev.grade.io.now(), "type": type(exc).__name__, "message": str(exc).replace(key, "[REDACTED]")}
                ev.grade.io.atomic_json(out / "collector-error.json", error)
                print("Collector retry:", error["type"], flush=True)
                time.sleep(30)


if __name__ == "__main__":
    main()
