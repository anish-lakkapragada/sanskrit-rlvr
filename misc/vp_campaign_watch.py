#!/usr/bin/env python3
"""Collect existing campaign jobs and refresh the report; never submit work."""
from __future__ import annotations
import argparse
import fcntl
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import vp_campaign as c, vp_campaign_analyze as analysis, oai_batch_eval as base
from misc.benchmark_forward import campaign_execution, iterative_goal_execution, parallel_search_execution


def refresh_report():
    if (ROOT / 'benchmarks/parallel-search-20261006/run.json').exists():
        from misc.vp_cartesian_analyze import analyze as analyze_cartesian
        analyze_cartesian()
        if (ROOT / 'benchmarks/parallel-search-20261006/prompt-probe-01/plan.json').exists():
            from misc.vp_cartesian_wording_analyze import analyze as analyze_wording
            analyze_wording()
    path = ROOT / "benchmarks/analysis/performance-study/study.json"
    study = base.read_json(path)
    study["moving_forward"]["execution"] = campaign_execution(ROOT)
    study["moving_forward"]["iterative_goal"] = iterative_goal_execution(ROOT)
    study["moving_forward"]["parallel_search"] = parallel_search_execution(ROOT)
    simple_section = None
    if (ROOT / 'benchmarks/parallel-search-20261007/coordinator-registration.json').exists():
        from misc.vp_simple_search_analyze import analyze as analyze_simple
        from misc.vp_simple_search_report import render as render_simple
        from misc.vp_simple_search_sensitivity import analyze as analyze_source_sensitivity
        if (ROOT / 'benchmarks/parallel-search-20261007/acceleration/plan.json').exists():
            from misc.vp_simple_search_fast_analyze import analyze as analyze_fast
            simple = analyze_fast()
        else:
            simple = analyze_simple()
            simple['source_sensitivity'] = analyze_source_sensitivity()
        if (ROOT / 'benchmarks/parallel-search-20261007/astra-comparison-01/plan.json').exists():
            from misc.vp_simple_astra_analyze import analyze as analyze_astra
            simple['astra_comparison'] = analyze_astra()
        from misc import vp_goal as goal
        if 'ending-screen-direct-20261007' in goal.load().get('submission_pools', {}):
            from misc.vp_ending_screen_analyze import analyze as analyze_ending
            simple['ending_screen'] = analyze_ending()
        else:
            queued = ROOT/'benchmarks/parallel-search-20261007/four_d-90/ending-screen-01/execution.json'
            if queued.exists():
                simple['ending_screen'] = {'state':'queued','received':0,'settled':0,'cost_upper_usd':0,
                    'committed_usd':0,'execution':base.read_json(queued)}
        final_dir = ROOT/'benchmarks/parallel-search-20261007/four_d-90/final1800-64k-01'
        if (final_dir/'execution-plan.json').exists():
            plan = base.read_json(final_dir/'execution-plan.json')
            execution = (base.read_json(final_dir/'execution.json') if (final_dir/'execution.json').exists()
                         else {'state':'prepared_pending_execution_review','providers':{}})
            simple['continuous_4d_final'] = {'plan':plan,'execution':execution,'benchmark_ready':False}
            if execution['state'] == 'complete_pending_paired_analysis':
                if (final_dir/'analysis.json').exists():
                    result = base.read_json(final_dir/'analysis.json')
                    if result['execution_plan_sha256'] != base.sha256(final_dir/'execution-plan.json'):
                        raise ValueError('Final analysis belongs to a different frozen run')
                else:
                    from misc.vp_continuous64k_analyze import analyze as analyze_final
                    result = analyze_final(final_dir)
                simple['continuous_4d_final']['analysis'] = result
            carry_result = final_dir/'astra-infrastructure-carry-01/analysis.json'
            if execution['state'] == 'complete_attempted_pending_paired_analysis' and carry_result.exists():
                result = base.read_json(carry_result)
                if (result['execution_plan_sha256'] != base.sha256(final_dir/'execution-plan.json')
                        or not result.get('numerical', {}).get('all_questions_attempted')):
                    raise ValueError('Infrastructure-aware analysis belongs to a different or unfinished cohort')
                simple['continuous_4d_final']['infrastructure_analysis'] = result
        study['moving_forward']['simple_search'] = simple
        simple_section = render_simple(simple)
        from misc import vp_goal as goal
        live = goal.load()
        base.atomic_json(ROOT / 'benchmarks/parallel-search-20261007/status.json', {
            'updated_at': base.now(),
            'tracks': {k: v['state'] for k, v in simple['tracks'].items()},
            'astra_comparison': {k: simple.get('astra_comparison', {}).get(k) for k in
                                 ('state', 'received', 'settled', 'cost_upper_usd', 'committed_usd', 'execution')},
            'ending_screen': {k: simple.get('ending_screen', {}).get(k) for k in
                             ('state', 'received', 'settled', 'cost_upper_usd', 'committed_usd', 'execution')},
            'continuous_4d_final': simple.get('continuous_4d_final', {}).get('execution'),
            'provider_caps_usd': {p: cfg['cap_micro']/1e6 for p, cfg in goal.PROVIDERS.items()},
            'committed_including_outstanding_maximums_usd': {p: goal.committed(live, p)/1e6 for p in goal.PROVIDERS},
            'protected_reserves_usd': {p: goal.protected_remaining(live, p)/1e6 for p in goal.PROVIDERS},
            'no_dhatu_public_modification_prompt': True,
            'held_source_pairs': (simple.get('source_sensitivity') or {}).get('held_pairs', 0),
            'benchmark_ready': False})
    payload = json.dumps(study, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    base.atomic_bytes(path, (payload + "\n").encode())
    safe = payload.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    template = (ROOT / "misc/benchmark_report.template.html").read_text()
    if simple_section is not None:
        start, end = '<!-- BEGIN SIMPLE VP SEARCH -->', '<!-- END SIMPLE VP SEARCH -->'
        assert template.count(start) == template.count(end) == 1
        before, rest = template.split(start)
        _, after = rest.split(end)
        template = before + start + '\n' + simple_section + '\n' + end + after
    assert template.count("__STUDY_DATA__") == 1
    base.atomic_bytes(ROOT / "benchmarks/report.html", template.replace("__STUDY_DATA__", safe).encode())


def watch():
    with (c.OUT / "collector.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        base.atomic_json(c.OUT / "collector.json", {"pid": os.getpid(), "started_at": base.now(),
                         "mode": "read-only collection; no generation or retries", "max_runtime_hours": 26})
        deadline = time.monotonic() + 26 * 3600
        while time.monotonic() < deadline:
            state = c.load()
            active = [j for j in state["jobs"].values() if j["batch_id"] and not j.get("collected_at")]
            if not active:
                refresh_report()
                break
            for job in active:
                try:
                    updated = c.collect(job["id"])
                    if updated.get("collected_at") and job["phase"] == "opus_screen":
                        analysis.analyze()
                except Exception as exc:
                    print(f"Collection error for {job['id']}: {type(exc).__name__}; no paid retry", flush=True)
            refresh_report()
            if all(j.get("collected_at") or not j["batch_id"] for j in c.load()["jobs"].values()):
                break
            time.sleep(30)
        base.atomic_json(c.OUT / "collector.json", {"pid": os.getpid(), "stopped_at": base.now(),
                         "mode": "read-only collection; no generation or retries"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-only", action="store_true")
    args = parser.parse_args()
    refresh_report() if args.refresh_only else watch()
