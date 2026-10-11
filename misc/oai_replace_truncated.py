#!/usr/bin/env python3
"""One authorized replacement of 2,048-token truncations, using a 6,000 cap.

Prepare is offline; submit issues each POST at most once. Collection replaces
only selected rows in the original JSON lists, with immutable source backups.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import oai_batch_eval as base

OLD_CAP = 2048
NEW_CAP = 6000
CONFIGS = [(m, e) for m in ("gpt-6-astra", "gpt-6-sol") for e in ("xhigh", "high")]
POLICY = "Keep original non-truncated results; replace each original 2048-token truncation once at 6000, regardless of either answer's correctness. No further retries."


def ledger(out):
    return out / "_batch/cap-6000/state.json"


def save_state(out, state):
    state["updated_at"] = base.now()
    base.atomic_json(ledger(out), state)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def body_of(row):
    body = ((row.get("raw_batch_result") or {}).get("response") or {}).get("body")
    return body if isinstance(body, dict) else {}


def eligible(row):
    response = (row.get("raw_batch_result") or {}).get("response") or {}
    body = body_of(row)
    return (row["request"]["body"].get("max_output_tokens") == OLD_CAP
            and response.get("status_code") == 200 and body.get("status") == "incomplete"
            and (body.get("incomplete_details") or {}).get("reason") == "max_output_tokens")


def usage_of(rows):
    usage = Counter()
    for row in rows:
        u = body_of(row).get("usage") or {}
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            usage[key] += u.get(key, 0)
        usage["reasoning_tokens"] += (u.get("output_tokens_details") or {}).get("reasoning_tokens", 0)
        details = u.get("input_tokens_details") or {}
        usage["cached_input_tokens"] += details.get("cached_tokens", 0)
        usage["cache_write_tokens"] += details.get("cache_write_tokens", 0)
    return dict(usage)


def cost_of(usage, model):
    rates = base.BATCH_RATES[model]
    cached = usage.get("cached_input_tokens", 0)
    written = usage.get("cache_write_tokens", 0)
    ordinary = usage.get("input_tokens", 0) - cached - written
    return (ordinary * rates["input"] + cached * rates["cached_input"]
            + written * rates["cache_write"] + usage.get("output_tokens", 0) * rates["output"]) / 1e6


def backup(path, payload):
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"Existing backup differs: {path}")
    else:
        base.atomic_bytes(path, payload)


def prepare(out):
    if ledger(out).exists():
        return base.read_json(ledger(out))
    state = {"schema_version": 1, "run_id": "cap6000-" + uuid4().hex[:12],
             "created_at": base.now(), "policy": POLICY,
             "old_max_output_tokens": OLD_CAP, "new_max_output_tokens": NEW_CAP,
             "sdk_max_retries": 0, "additional_attempts_per_selected_task": 1,
             "configurations": {}}
    for model, effort in CONFIGS:
        slug = f"{model}-{effort}"
        paths = base.configuration_paths(out, slug)
        if not paths["result"].exists():
            continue
        source_bytes = paths["result"].read_bytes()
        original = json.loads(source_bytes)
        if not isinstance(original, list) or not original:
            raise ValueError(f"Expected a nonempty JSON list: {paths['result']}")
        if len({r["custom_id"] for r in original}) != len(original):
            raise ValueError("Duplicate source custom_id")
        if len({r["task_id"] for r in original}) != len(original):
            raise ValueError("Duplicate source task_id")
        if any(r["raw_batch_result"] is None for r in original):
            raise ValueError("Original run must be collected before preparing replacements")
        selected = [r for r in original if eligible(r)]
        if not selected:
            continue
        requests = []
        for row in selected:
            request = copy.deepcopy(row["request"])
            body = request["body"]
            if (body["model"] != model or body["reasoning"] != {"mode": "standard", "effort": effort}
                    or body.get("tools") != [] or body.get("tool_choice") != "none"):
                raise ValueError("Source request does not match the authorized model/effort/tool settings")
            body["max_output_tokens"] = NEW_CAP
            requests.append(request)
        work = paths["work"] / "cap-6000"
        backup(work / "original-results.json", source_bytes)
        backup(work / "original-meta.json", paths["meta"].read_bytes())
        payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in requests).encode("utf-8")
        backup(work / "input.jsonl", payload)
        state["configurations"][slug] = {
            "model": model, "effort": effort, "task_count": len(selected), "full_task_count": len(original),
            "selected_custom_ids": [r["custom_id"] for r in selected],
            "result_path": str(paths["result"].relative_to(out)),
            "meta_path": str(paths["meta"].relative_to(out)), "work_dir": str(work.relative_to(out)),
            "original_sha256": digest(source_bytes), "input_sha256": digest(payload),
            "original_meta_sha256": base.sha256(work / "original-meta.json"),
            "status": "prepared", "input_file_id": None, "batch_id": None, "batch": None,
            "upload_attempted_at": None, "submit_attempted_at": None, "submission_error": None,
            "results_ready_at": None, "collected_at": None,
            "maximum_additional_cost_usd_at_460_input_tokens": len(selected)
                * (460 * base.BATCH_RATES[model]["input"] + NEW_CAP * base.BATCH_RATES[model]["output"]) / 1e6,
        }
    if not state["configurations"]:
        raise ValueError("No eligible 2048-token truncations found")
    save_state(out, state)
    return state


def checked_original(out, cfg):
    path = out / cfg["work_dir"] / "original-results.json"
    if base.sha256(path) != cfg["original_sha256"]:
        raise ValueError("Original-result backup hash mismatch")
    return base.read_json(path)


def update_meta(out, state, slug, rows=None):
    cfg = state["configurations"][slug]
    source_meta = out / cfg["work_dir"] / "original-meta.json"
    if base.sha256(source_meta) != cfg["original_meta_sha256"]:
        raise ValueError("Original-metadata backup hash mismatch")
    meta = base.read_json(source_meta)
    extension = {"run_id": state["run_id"], "policy": POLICY,
                 "state_path": str(ledger(out).relative_to(out)),
                 **{k: cfg.get(k) for k in ("status", "batch_id", "task_count", "full_task_count",
                    "submit_attempted_at", "results_ready_at", "collected_at", "original_sha256",
                    "result_sha256", "work_dir", "submission_error", "last_collection_error",
                    "cancel_requested_at", "replacement_disabled_at", "replacement_disabled_reason",
                    "replacement_applied", "archived_result_count")}}
    meta["cap_extension"] = extension
    if rows is not None:
        originals = checked_original(out, cfg)
        new_rows = base.read_json(out / cfg["work_dir"] / "replacements.json")
        meta["max_output_tokens"] = None
        meta["max_output_tokens_by_attempt"] = {"1": OLD_CAP, "2": NEW_CAP}
        meta["retained_request_cap_counts"] = dict(Counter(str(r["request"]["body"]["max_output_tokens"]) for r in rows))
        meta["evaluation_max_output_tokens"] = NEW_CAP
        meta["uniform_request_cap"] = len(meta["retained_request_cap_counts"]) == 1
        meta["output_token_cap_note"] = (
            "Maximum per-response budget: 6000 tokens, including reasoning and visible output. "
            "Completed 2048-cap responses were retained; only original truncations were rerun once at 6000.")
        meta["attempt_count_distribution"] = {"1": len(rows) - len(new_rows), "2": len(new_rows)}
        meta["evaluation_protocol"] = POLICY
        meta["summary"] = {**base.summarize(rows), "final": True}
        meta["usage_totals"] = usage_of(rows)
        all_usage = Counter(usage_of(originals))
        all_usage.update(usage_of(new_rows))
        meta["usage_totals_all_attempts"] = dict(all_usage)
        meta["estimated_cost_usd_all_attempts"] = cost_of(all_usage, cfg["model"])
        extension["original_summary"] = base.summarize(originals)
        extension["replacement_summary"] = base.summarize(new_rows)
        extension["usage_totals"] = usage_of(new_rows)
        extension["estimated_additional_cost_usd"] = cost_of(usage_of(new_rows), cfg["model"])
        extension["cost_is_usage_estimate_not_invoice"] = True
    base.atomic_json(out / cfg["meta_path"], meta)


def submit_one(client, out, state, slug):
    cfg = state["configurations"][slug]
    if cfg["batch_id"] or cfg["submit_attempted_at"] or cfg["submission_error"] or cfg.get("replacement_disabled_at"):
        return
    work = out / cfg["work_dir"]
    if base.sha256(work / "input.jsonl") != cfg["input_sha256"]:
        raise ValueError("Replacement input hash mismatch")
    if base.sha256(out / cfg["result_path"]) != cfg["original_sha256"]:
        raise ValueError("Source results changed after prepare")
    try:
        if not cfg["input_file_id"]:
            if cfg["upload_attempted_at"]:
                return
            cfg.update(upload_attempted_at=base.now(), status="uploading")
            save_state(out, state)
            with (work / "input.jsonl").open("rb") as f:
                raw = client.files.with_raw_response.create(file=f, purpose="batch")
            uploaded = base.capture_json(work / "upload.http.json", raw)
            cfg.update(input_file_id=uploaded["id"], status="uploaded")
            save_state(out, state)
        cfg.update(submit_attempted_at=base.now(), status="submission_unknown")
        save_state(out, state)
        raw = client.batches.with_raw_response.create(
            input_file_id=cfg["input_file_id"], endpoint="/v1/responses", completion_window="24h",
            metadata={"run_id": state["run_id"], "configuration": slug, "purpose": "replace_2048_truncations",
                      "task_count": str(cfg["task_count"]), "max_output_tokens": str(NEW_CAP), "retries": "0"})
        batch = base.capture_json(work / "create.http.json", raw)
        cfg.update(batch_id=batch["id"], batch=batch, status=batch["status"])
        save_state(out, state)
    except Exception as exc:
        cfg["submission_error"] = base.error_details(exc, client)
        cfg["status"] = "submission_unknown" if cfg["submit_attempted_at"] else "upload_failed"
        save_state(out, state)
    update_meta(out, state, slug)
    print(f"{slug}: {cfg['status']} {cfg['batch_id'] or ''}", flush=True)


def recover_submission(client, out, state, cfg):
    """Reconcile uncertain POST outcomes using only receipts and GET requests."""
    work = out / cfg["work_dir"]
    if not cfg["input_file_id"] and (work / "upload.http.json").exists():
        cfg["input_file_id"] = base.read_json(work / "upload.http.json")["body"]["id"]
        save_state(out, state)
    if cfg["batch_id"] or not cfg["submit_attempted_at"]:
        return
    if (work / "create.http.json").exists():
        matches = [base.read_json(work / "create.http.json")["body"]]
    else:
        matches, after = [], None
        while True:
            raw = client.batches.with_raw_response.list(limit=100, **({"after": after} if after else {}))
            page = base.capture_json(work / f"recovery-{uuid4().hex}.http.json", raw)
            matches.extend(b for b in page["data"] if b.get("input_file_id") == cfg["input_file_id"]
                           and (b.get("metadata") or {}).get("run_id") == state["run_id"])
            if not page.get("has_more") or not page["data"]:
                break
            after = page["data"][-1]["id"]
    if len(matches) > 1:
        raise ValueError("Multiple batches match one replacement submission")
    if matches:
        batch = matches[0]
        cfg.update(batch_id=batch["id"], batch=batch, status=batch["status"], recovered_at=base.now())
        save_state(out, state)


def build_replacements(originals, cfg, state, results):
    selected = set(cfg["selected_custom_ids"])
    seeds = []
    for row in originals:
        if row["custom_id"] not in selected:
            continue
        if not eligible(row):
            raise ValueError("Selected original is not an eligible truncation")
        request = copy.deepcopy(row["request"])
        request["body"]["max_output_tokens"] = NEW_CAP
        new = base.base_record(row["task"], row["task_index"], request, state["run_id"], row["configuration"])
        new["batch_submitted_at"] = cfg["submit_attempted_at"]
        new["attempt_number"] = 2
        new["replacement"] = {"reason": "original_max_output_tokens", "previous_max_output_tokens": OLD_CAP,
            "previous_run_id": row["run_id"], "previous_batch_id": row["batch_id"],
            "previous_response_id": body_of(row).get("id"),
            "previous_record_path": cfg["work_dir"] + "/original-results.json",
            "previous_custom_id": row["custom_id"], "previous_record_sha256": digest(json_bytes(row))}
        seeds.append(new)
    if len(seeds) != len(selected):
        raise ValueError("Selected IDs missing from original snapshot")
    return base.assemble(seeds, results, cfg["batch"], cfg["results_ready_at"])


def merge_rows(originals, replacements, selected_ids):
    selected = set(selected_ids)
    if len(selected) != len(selected_ids) or not selected.issubset({r["custom_id"] for r in originals}):
        raise ValueError("Selected IDs must be unique and present in the original list")
    by_id = {r["custom_id"]: r for r in replacements}
    if len(by_id) != len(replacements) or set(by_id) != selected:
        raise ValueError("Replacement IDs must exactly match the selected set")
    merged = []
    for original in originals:
        replacement = by_id.get(original["custom_id"])
        if replacement is None:
            merged.append(original)
            continue
        if any(replacement[k] != original[k] for k in
               ("task_id", "task", "task_index", "configuration", "sample_index")):
            raise ValueError("Replacement changed task identity")
        expected_request = copy.deepcopy(original["request"])
        expected_request["body"]["max_output_tokens"] = NEW_CAP
        if replacement["request"] != expected_request:
            raise ValueError("Replacement request changed something other than the cap")
        merged.append(replacement)
    if len(merged) != len(originals) or len({r["custom_id"] for r in merged}) != len(merged):
        raise ValueError("Merged list changed cardinality")
    return merged


def commit_replacements(out, state, slug):
    cfg = state["configurations"][slug]
    if cfg.get("replacement_disabled_at"):
        raise ValueError("User disabled replacement; preserving the existing result file")
    replacements_path = out / cfg["work_dir"] / "replacements.json"
    if base.sha256(replacements_path) != cfg["replacements_sha256"]:
        raise ValueError("Replacement-result hash mismatch")
    original = checked_original(out, cfg)
    rows = merge_rows(original, base.read_json(replacements_path), cfg["selected_custom_ids"])
    payload = json_bytes(rows)
    expected_hash = digest(payload)
    destination = out / cfg["result_path"]
    # Accept our exact previous commit after a crash, but never overwrite other edits.
    current_hash = base.sha256(destination)
    if current_hash not in {cfg["original_sha256"], expected_hash}:
        raise ValueError("Destination changed externally; refusing to overwrite it")
    if current_hash != expected_hash:
        base.atomic_bytes(destination, payload)
    cfg["result_sha256"] = expected_hash
    cfg["collected_at"] = cfg["results_ready_at"]
    try:
        cfg.pop("last_collection_error", None)
        update_meta(out, state, slug, rows)
        save_state(out, state)
    except Exception:
        # A later collection repairs metadata after an interrupted commit,
        # accepting only the exact result bytes we computed above.
        cfg["collected_at"] = None
        raise
    print(f"Replaced {len(cfg['selected_custom_ids'])} rows in {cfg['result_path']}; "
          f"{json.dumps(base.summarize(rows))}", flush=True)


def download_results(client, work, batch):
    results = []
    for key in ("output_file_id", "error_file_id"):
        file_id = batch.get(key)
        if not file_id:
            continue
        path = work / (file_id + ".jsonl")
        if not path.exists():
            raw = client.files.with_raw_response.content(file_id)
            data = raw.http_response.content
            for line in data.splitlines():
                if line.strip():
                    json.loads(line)
            base.atomic_bytes(path, data)
            base.atomic_json(path.with_suffix(".http.json"), {"received_at": base.now(),
                "status_code": raw.status_code, "headers": list(raw.headers.multi_items()),
                "sha256": digest(data), "body_path": path.name})
        results.extend(json.loads(line) for line in path.read_text().splitlines() if line.strip())
    return results


def collect(client, out, state):
    for slug, cfg in state["configurations"].items():
        if cfg["collected_at"]:
            continue
        try:
            if cfg["results_ready_at"] and not cfg.get("replacement_disabled_at"):
                commit_replacements(out, state, slug)
                continue
            recover_submission(client, out, state, cfg)
            if not cfg["batch_id"]:
                continue
            work = out / cfg["work_dir"]
            raw = client.batches.with_raw_response.retrieve(cfg["batch_id"])
            batch = base.capture_json(work / "status.http.json", raw)
            with (work / "polls.jsonl").open("a") as f:
                f.write(json.dumps({"received_at": base.now(), "body": batch}) + "\n")
            cfg.update(batch=batch, status=batch["status"])
            save_state(out, state)
            if batch["status"] not in base.TERMINAL:
                update_meta(out, state, slug)
                continue
            results = download_results(client, work, batch)
            if cfg.get("replacement_disabled_at"):
                # Explicit user cancellation stops this configuration's merge.
                # Preserve even late partial responses as separate raw artifacts.
                base.atomic_json(work / "cancelled-results.json", results)
                cfg.update(collected_at=base.now(), replacement_applied=False,
                           archived_result_count=len(results))
                try:
                    cfg.pop("last_collection_error", None)
                    update_meta(out, state, slug)
                    save_state(out, state)
                except Exception:
                    cfg["collected_at"] = None
                    raise
                print(f"{slug}: {batch['status']}; archived {len(results)} results; existing JSON preserved", flush=True)
                continue
            # Persist the timestamp and result hash together, after assembling.
            ready_cfg = {**cfg, "results_ready_at": base.now()}
            replacements = build_replacements(checked_original(out, cfg), ready_cfg, state, results)
            base.atomic_json(work / "replacements.json", replacements)
            cfg.update(results_ready_at=ready_cfg["results_ready_at"],
                       replacements_sha256=base.sha256(work / "replacements.json"))
            save_state(out, state)
            commit_replacements(out, state, slug)
        except Exception as exc:
            cfg["last_collection_error"] = base.error_details(exc, client)
            save_state(out, state)
            print(f"{slug}: collection {type(exc).__name__}; no generation retry", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "submit", "collect", "watch", "status"))
    parser.add_argument("--out", type=Path, default=ROOT / "benchmarks/oai")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    out = args.out.resolve()
    if args.command in {"prepare", "status"}:
        with base.lock(out):
            state = prepare(out) if args.command == "prepare" else base.read_json(ledger(out))
            print(base.status_lines(state), flush=True)
            for slug, cfg in state["configurations"].items():
                print(f"{slug}: {cfg['task_count']} selected / {cfg['full_task_count']}; "
                      f"maximum new cost ${cfg['maximum_additional_cost_usd_at_460_input_tokens']:.2f}")
        return
    client = base.api_client()
    try:
        if args.command == "submit":
            with base.lock(out):
                state = base.read_json(ledger(out))
                for slug in state["configurations"]:
                    submit_one(client, out, state, slug)
            return
        last_status = None
        while True:
            with base.lock(out):
                state = base.read_json(ledger(out))
                collect(client, out, state)
                current = base.status_lines(state)
                if current != last_status:
                    print(base.now() + "\n" + current, flush=True)
                    last_status = current
                active = any((c["batch_id"] or c["submit_attempted_at"]) and not c["collected_at"]
                             for c in state["configurations"].values())
                base.atomic_json(ledger(out).parent / "watcher-status.json", {
                    "checked_at": base.now(), "active": active,
                    "all_collected": all(c["collected_at"] for c in state["configurations"].values())})
            if args.command == "collect" or not active:
                break
            time.sleep(max(1, min(args.interval, 60)))
    finally:
        client.close()


if __name__ == "__main__":
    main()
