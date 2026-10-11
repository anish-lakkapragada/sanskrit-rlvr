"""Bounded cleanup for only the Lambda instances recorded by this benchmark."""

import argparse
import base64
import datetime
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


def api(endpoint, payload=None):
    key = os.environ.get("LAMBDA_API_KEY") or os.environ.get("LAMBDA_CLOUD_API_KEY")
    if not key:
        raise RuntimeError("Lambda credential missing")
    headers = {"Authorization": "Basic " + base64.b64encode((key + ":").encode()).decode(),
               "User-Agent": "curl/8.7.1", "Content-Type": "application/json"}
    req = urllib.request.Request("https://cloud.lambdalabs.com/api/v1/" + endpoint,
                                 headers=headers, data=None if payload is None else json.dumps(payload).encode())
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--hours", type=float, default=6)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--terminate", action="store_true")
    args = ap.parse_args()
    state_file = args.run_dir / "cloud.json"
    while True:
        try:
            state = json.loads(state_file.read_text())
            owned = set(state["instance_ids"])
            instances = [i for i in api("instances")["data"] if i["id"] in owned]
            concise = [{k: i.get(k) for k in ("id", "name", "status", "ip")} for i in instances]
            (args.run_dir / "instances.json").write_text(json.dumps(concise, indent=2) + "\n")
            if args.status:
                print(json.dumps(concise, indent=2))
                return
            launched = datetime.datetime.fromisoformat(state["launched_at"])
            elapsed = (datetime.datetime.now(datetime.timezone.utc) - launched).total_seconds()
            collected = (args.run_dir / "collected.json").exists()
            if args.terminate or collected or elapsed >= args.hours * 3600:
                live = [i["id"] for i in instances if i["status"] not in ("terminated", "terminating")]
                if live:
                    api("instance-operations/terminate", {"instance_ids": live})
                    print(json.dumps({"terminate_requested": live, "reason": "manual" if args.terminate else "collected" if collected else "deadline"}), flush=True)
                if not instances:
                    (args.run_dir / "terminated.json").write_text(json.dumps({"instance_ids": sorted(owned), "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}) + "\n")
                    print("All benchmark instances verified absent", flush=True)
                    return
            time.sleep(30)
        except (OSError, urllib.error.HTTPError, KeyError, ValueError) as exc:
            print("Watchdog retry:", type(exc).__name__, getattr(exc, "code", ""), flush=True)
            if args.status:
                raise
            time.sleep(30)


if __name__ == "__main__":
    main()
