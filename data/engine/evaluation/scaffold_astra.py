"""Create the Astra evaluation manifest and schema locally; never sends requests.

Run: python3 data/engine/evaluation/scaffold_astra.py
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation.scoring import STATUSES, VERSION

RUN = ROOT / "data/benchmark/results/astra-xhigh"
FAMILIES = ("tinanta", "taddhitanta", "krdanta", "subanta")
REQUEST_DEFAULTS = {
    "model": "gpt-6-astra", "reasoning": {"effort": "xhigh"},
    "service_tier": "default", "store": False, "stream": True,
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def descriptor(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "sha256": digest(raw), "bytes": len(raw)}


def obj(properties, **extra):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False, **extra}


def schema():
    nullable_string = {"type": ["string", "null"]}
    nullable_number = {"type": ["number", "null"], "minimum": 0}
    token_count = {"type": "integer", "minimum": 0}
    record = obj({
        "task_id": {"type": "string", "minLength": 1,
                    "description": "Join to the original benchmark row for inputs and accepted answers."},
        "attempt_number": {"type": "integer", "minimum": 1},
        "status": {"enum": list(STATUSES)},
        "output_text": {"type": "string", "description": "Unmodified visible response text, including any available partial text."},
        "answer": nullable_string,
        "correct": {"type": ["boolean", "null"], "description": "Exact membership in the source gold list for completed responses; null for other outcomes."},
        "format_ok": {"type": "boolean", "description": "One nonempty answer block; only whitespace outside; no nested markup."},
        "usage": {
            "type": ["object", "null"],
            "description": "Full provider usage. Output length is usage.output_tokens; reasoning is its subset. Null when unavailable.",
            "properties": {
                "input_tokens": token_count, "output_tokens": token_count, "total_tokens": token_count,
                "input_tokens_details": {"type": "object", "additionalProperties": True},
                "output_tokens_details": {"type": "object", "additionalProperties": True},
            },
            "required": ["input_tokens", "output_tokens"], "additionalProperties": True,
        },
        "cost_usd": {**nullable_number, "description": "Usage-based estimate using the manifest rates; null when unknown."},
        "request_id": nullable_string, "response_id": nullable_string,
        "elapsed_ms": nullable_number,
        "error": {"type": ["object", "null"], "additionalProperties": True,
                  "description": "Null on normal success; otherwise compact error/refusal/incomplete or unknown-cost details, preserving provider codes/messages."},
    })
    record["allOf"] = [
        {"if": {"properties": {"status": {"const": "completed"}}},
         "then": {"properties": {"correct": {"type": "boolean"}}},
         "else": {"properties": {"correct": {"type": "null"}}}},
        {"if": {"properties": {"usage": {"type": "null"}}},
         "then": {"properties": {"cost_usd": {"type": "null"}}}},
    ]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Compact Astra xHigh benchmark family results (v2)",
        "description": "One array per family; one row per task, selecting the latest explicitly authorized settled attempt. All earlier attempts remain in the journals.",
        "type": "array", "items": {"$ref": "#/$defs/result"}, "$defs": {"result": record},
    }


def build():
    RUN.mkdir(parents=True, exist_ok=True)
    if any((RUN / folder).exists() for folder in ("receipts", "journals")) or any((RUN / f"{family}.json").exists() for family in FAMILIES):
        raise RuntimeError("Run artifacts exist; keep the prepared manifest immutable once execution starts")
    manifest_path = RUN / "manifest.json"
    previous = json.loads(manifest_path.read_bytes()) if manifest_path.exists() else None
    if previous and previous.get("status") != "scaffolded":
        raise RuntimeError("An active run manifest cannot be regenerated")
    entries = []
    for family in FAMILIES:
        dataset = ROOT / f"data/benchmark/{family}/{family}.json"
        sampling_manifest = dataset.with_suffix(".manifest.json")
        rows = json.loads(dataset.read_bytes())
        sampling = json.loads(sampling_manifest.read_bytes())
        desc = descriptor(dataset)
        assert desc["sha256"] == sampling["output"]["sha256"]
        assert len(rows) == len({row["id"] for row in rows}) == 5000
        template = ROOT / f"data/engine/prompts/v2/vp_{family}.txt"
        renderer = ROOT / f"data/engine/{family}/common.py"
        entries.append({
            "family": family, "dataset": {**desc, "records": len(rows)},
            "sampling_manifest": descriptor(sampling_manifest),
            "prompt_template": {**descriptor(template), "text": template.read_text(encoding="utf-8")},
            "renderer": {**descriptor(renderer), "callable": f"data.engine.{family}.common.render_task"},
            "result_file": f"{family}.json", "journal_file": f"journals/{family}.jsonl",
            "order": "benchmark source row order; one selected attempt per task",
        })
    schema_payload = (json.dumps(schema(), ensure_ascii=False, indent=2) + "\n").encode()
    manifest = {
        "schema_version": 2, "run_id": "astra-xhigh", "status": "scaffolded",
        "created_at": previous["created_at"] if previous else datetime.now(timezone.utc).isoformat(),
        "started_at": None, "finished_at": None, "planned_tasks": 20000,
        "planned_primary_requests": 20000, "submitted_requests": 0,
        "path_conventions": {"inputs_and_code": "repository-relative", "results_and_journals": "run-directory-relative"},
        "provider": "openai", "api": {"method": "POST", "url": "https://api.openai.com/v1/responses"},
        "request_defaults": REQUEST_DEFAULTS,
        "request_input": "Exact rendered prompt as request.input; one independent request per task; no conversation history, extra instructions, or tools.",
        "output_limit": {"benchmark_cap": None, "max_output_tokens_parameter": "omitted",
                         "meaning": "No benchmark-imposed token cap. Provider/model limits still apply.",
                         "documented_model_max_output_tokens": 128000},
        "omitted_request_parameters": ["max_output_tokens", "temperature", "top_p", "seed", "instructions", "previous_response_id", "tools"],
        "sampling_seed": 69, "sampling_seed_scope": "Dataset selection only; not a model-generation seed.",
        "rendering_dependencies": {"python": "3.11+", "vidyut": "0.4.0"},
        "tasks": entries,
        "result_schema": {"path": "result.schema.json", "sha256": digest(schema_payload)},
        "scoring": {
            "version": VERSION, "implementation": descriptor(Path(__file__).with_name("scoring.py")),
            "answer_extraction": "Extract exactly one well-formed literal <answer>...</answer> block and strip outer answer whitespace. No Unicode or orthographic normalization. Original text stays in output_text.",
            "correct": "For completed responses: answer is not null and answer in the source task.gold_devanagari list, joined by task_id. Otherwise null.",
            "format_ok": "Exactly one nonempty answer block, no nested markup, and only whitespace outside the block.",
            "strict_accuracy": "Derived when reporting: correct is true and format_ok. Not duplicated in result rows.",
            "primary_attempt": 1,
            "reporting": "Report correctness and format separately, plus strict accuracy over all 20,000 tasks using the latest explicitly authorized settled attempt per task. Report refusals/incomplete/errors separately; never drop tasks from the denominator. Preserve first-attempt results in journals for separate analysis.",
        },
        "pricing": {
            "snapshot_id": "openai-astra-standard-2026-10-14", "verified_date": "2026-10-14",
            "currency": "USD", "tier": "standard", "endpoint": "global direct OpenAI",
            "rates_usd_per_million_tokens": {"uncached_input": 10, "cached_input": 1, "cache_write_input": 12.5, "output": 50},
            "long_context_threshold_input_tokens": 272000,
            "long_context_rates_usd_per_million_tokens": {"uncached_input": 20, "cached_input": 2, "cache_write_input": 25, "output": 75},
            "formula": "((input_tokens - cached_tokens - cache_write_tokens) * uncached_input_rate + cached_tokens * cached_input_rate + cache_write_tokens * cache_write_input_rate + output_tokens * output_rate) / 1000000",
            "rules": ["Output usage already includes reasoning tokens; do not bill them twice.",
                      "Preserve full usage; rates are stored once in this manifest. Check cache counters and the journal response tier before calculating.",
                      "Missing usage or unsupported billing details produce cost_usd=null with a reason; do not treat unknown cost as zero.",
                      "Cost is a token-usage estimate, not an invoice receipt; excludes credits, taxes and account-specific adjustments.",
                      "Aggregate cost across all attempts, including failed or refused attempts with usage and any explicit retries."],
            "sources": ["https://developers.openai.com/api/docs/models/gpt-6-astra", "https://developers.openai.com/api/docs/pricing"],
        },
        "preservation": {
            "journal_path_pattern": "journals/{family}.jsonl",
            "completed_archive_pattern": "journals/{family}.jsonl.gz",
            "journal_count": 4, "journal_key": ["task_id", "attempt_number"],
            "events": {
                "started": "Before sending, append and fsync task_id, attempt_number, timestamp, client_request_id and exact request JSON including the hydrated prompt.",
                "response": "Before scoring, append and fsync task_id, attempt_number, request_id, elapsed_ms, timestamp and the complete unmodified terminal response.",
                "error": "Append task_id, attempt_number, request_id, timestamp, elapsed_ms, HTTP status, provider/client error details and available partial output; exclude credentials.",
            },
            "per_request_files": False, "save_full_stream_events": False,
            "stream_handling": "Consume events in memory. Preserve available partial text on handled interruption; do not permanently log individual events.",
            "result_encoding": "Compact UTF-8 JSON arrays; one compact record per line.",
            "shared_metadata": "Dataset/gold stay in pinned benchmark files. Model/settings/templates/rates/scoring version stay in this manifest; family comes from the result filename.",
            "write_order": "Durable started journal entry before send; durable response/error entry before scoring; atomically update family results after each settled attempt.",
            "compression": "Gzip each completed journal; remove the plain copy only after verifying the archive. Retain one archive per family.",
            "recovery": "Replay journals to rebuild results and reprice/rescore offline. Read completed .jsonl.gz archives as needed; do not resend completed attempts.",
        },
        "execution": {
            "state": "not_started", "runner_implemented": False, "concurrency": None,
            "automatic_retries": 0, "model_fallbacks": [],
            "resume": "Reuse terminal journal entries. A started request without a response/error entry is unresolved and must not be automatically resent.",
            "explicit_retries": "Only explicit retry batches may resend infrastructure failures. Append a new attempt_number to the journal, replace the selected result row in place, and retain all earlier attempts and costs.",
            "preflight": "Validate dataset, template, renderer, scoring and schema hashes before sending; record runtime/library versions and runner hash when implemented.",
            "runtime_versions": None, "runner": None,
        },
        "scaffold_generator": descriptor(Path(__file__)),
        "official_references": ["https://developers.openai.com/api/reference/resources/responses/methods/create",
                                "https://developers.openai.com/api/docs/guides/token-counting"],
    }
    (RUN / "result.schema.json").write_bytes(schema_payload)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {manifest_path.relative_to(ROOT)} for 20,000 tasks. No API calls made.")


if __name__ == "__main__":
    build()
