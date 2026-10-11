"""Local read-only dashboard and completion sounds for the two research workers.

No provider calls. The only writes are monitor metadata and notification receipts.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc.vp_cartesian_visibility import PILOT08_JOBS, pending_confirmation_ids, visible_release_job
from misc import vp_goal as runner
OUT = ROOT / 'benchmarks/parallel-search-20261006'
LEDGER = ROOT / 'benchmarks/iterative-goal-20261006/ledger.json'
TRACKS = ('four_d', 'five_d')
TERMINAL = {'completed', 'blocked', 'failed'}
CAPS = {'Anthropic': 1000, 'OpenAI': 2000}


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path, default=None):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {} if default is None else default


def write(path, value):
    temporary = path.with_name(path.name + '.monitor.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def snapshot():
    ledger = read(LEDGER)
    analysis = read(OUT / 'development-results.json').get('experiments', {})
    current_policy = read(OUT / 'plan.json').get('oracle_policy', '')
    supplement_name = 'scope-supplement-' + current_policy.replace('oracle-policy-', 'policy')
    confirmation_dir = OUT / 'five_d/pilot-07/revision-01'
    confirmation_manifest = read(confirmation_dir / 'coordinator-execution.json')
    confirmation_jobs = [ledger['jobs'].get(c['id'], {})
                         for c in confirmation_manifest.get('chunks', [])]
    confirmation_complete = bool(confirmation_jobs) and all(
        j.get('settled') and j.get('collected_at') for j in confirmation_jobs)
    paired_relative = read(OUT / 'run.json').get('active_paired_confirmation', 'five_d/pilot-08')
    paired_dir = OUT / paired_relative
    paired_plan = read(paired_dir / 'plan.json')
    paired_jobs = [ledger['jobs'].get(key, {'id': key, 'status': 'unregistered'})
                   for key in PILOT08_JOBS]
    withheld = pending_confirmation_ids(ledger)
    public_jobs = [visible_release_job(ledger, j) for j in ledger['jobs'].values()]
    budgets = {}
    for provider, cap in CAPS.items():
        jobs = [j for j in ledger['jobs'].values() if j['provider'] == provider]
        historical = ledger['historical_spend_micro'][provider]
        settled = historical + sum(j.get('actual_cost_upper_micro', 0) for j in jobs if j.get('settled'))
        pending = sum(j.get('reservation_micro', 0) for j in jobs if not j.get('settled'))
        budgets[provider] = {'cap': cap, 'spent': settled / 1e6, 'pending_max': pending / 1e6,
                             'remaining_after_pending': cap - (settled + pending) / 1e6}
    tracks = []
    for track in TRACKS:
        state = read(OUT / track / 'status.json')
        progress = OUT / track / 'progress.md'
        state['progress_tail'] = progress.read_text()[-10000:] if progress.exists() else ''
        state['track'] = track
        tag = track.replace('_', '-')
        state['evaluations'] = [
            {'id': j['id'], 'provider': j['provider'], 'n': j['n'], 'status': j['status'],
             'effort': ledger['phase_policy'][j['phase']][0],
             'max_output_tokens': ledger['phase_policy'][j['phase']][1],
             'summary': j.get('summary'), 'collected_at': j.get('collected_at'),
             'completed_answers': j.get('completed_answers'),
             'completed_correct': j.get('completed_correct'),
             'provider_progress': j.get('batch', {}).get('request_counts'),
             'scores_embargoed': j.get('scores_embargoed', False),
             'analysis_status': ('Awaiting the entire fixed release for both references' if j.get('scores_embargoed') else None),
             'within_current_scope': None if j.get('scores_embargoed') else analysis.get(j['id'], {}).get('within_current_scope'),
             'excluded_by_current_scope': 0 if j.get('scores_embargoed') else len(analysis.get(j['id'], {}).get('excluded', [])),
             'cost_usd': j.get('actual_cost_upper_micro', 0) / 1e6,
             'maximum_reserved_usd': j.get('reservation_micro', 0) / 1e6}
            for j in public_jobs if f'-{tag}-' in j['id']
            and j['phase'] in ({'explore', 'confirm', 'confirm_64k'} | (runner.FINAL_PHASES - {'cap_check'}))]
        tracks.append(state)
    # Keep the fixed panel's intermediate outcomes out of the progress display.
    # Financial and provider completion counts remain visible throughout.
    if not confirmation_complete:
        pending_ids = {j.get('id') for j in confirmation_jobs}
        for track in tracks:
            for job in track['evaluations']:
                if job['id'] in pending_ids:
                    for key in ('summary', 'completed_answers', 'completed_correct', 'within_current_scope'):
                        job[key] = None
                    job['excluded_by_current_scope'] = 0
                    job['analysis_status'] = 'Awaiting both fixed confirmation chunks'
    for track in tracks:
        for job in track['evaluations']:
            if job['id'] in withheld:
                for key in ('summary', 'completed_answers', 'completed_correct', 'within_current_scope'):
                    job[key] = None
                job['excluded_by_current_scope'] = 0
                job['analysis_status'] = 'Awaiting all six Opus and two Astra chunks'
    return {'updated_at': now(), 'tracks': tracks, 'budgets': budgets,
            'monitor': read(OUT / 'monitor-process.json'),
            'oracle_policy': current_policy,
            'wording_diagnostic': read(OUT / 'prompt-probe-01/results.json'),
            'cap_diagnostic': {
                'plan': read(OUT / 'five_d/astra-cap-development-01.plan.json'),
                'analysis': read(OUT / 'five_d/astra-cap-development-01.analysis.json'),
                'job': {k:v for k,v in ledger['jobs'].get('astra-five-d-cap-development-01', {}).items()
                        if k in {'id','n','status','collected_at','reservation_micro','actual_cost_upper_micro'}},
                'provider_progress': ledger['jobs'].get('astra-five-d-cap-development-01', {}).get('batch', {}).get('request_counts')},
            'fixed_confirmation': {
                'n': confirmation_manifest.get('fixed_n'),
                'scope_supplement': read(confirmation_dir / supplement_name),
                'scope_supplement_file': supplement_name,
                'execution': read(confirmation_dir / 'coordinator-execution.execution.json'),
                'analysis_ready': confirmation_complete,
                'analysis': read(confirmation_dir / 'aggregate-analysis.json') if confirmation_complete else {},
                'jobs': [{k:j.get(k) for k in ('id','n','status','settled','collected_at')}
                         | {'provider_progress': j.get('batch', {}).get('request_counts')}
                         for j in confirmation_jobs]},
            'paired_confirmation': {
                'directory': paired_relative + '/', 'plan': paired_plan,
                'families': read(paired_dir / 'manifest.json').get('family_count'),
                'handoff_status': read(paired_dir / 'preflight-handoff.json').get('status'),
                'review': read(paired_dir / 'coordinator-source-review.json').get('status'),
                'analysis_ready': not withheld,
                'analysis': read(paired_dir / 'aggregate-analysis.json') if not withheld else {},
                'executions': {p: read(paired_dir / f'coordinator-{p}-execution.execution.json')
                               for p in ('opus', 'astra')},
                'jobs': [{k: j.get(k) for k in ('id', 'n', 'status', 'settled', 'collected_at')}
                         | {'provider_progress': j.get('batch', {}).get('request_counts')}
                         for j in paired_jobs]},
            'notifications': read(OUT / 'notifications.json', {'events': []})['events'][-10:]}


def play_sound():
    try:
        result = subprocess.run(['/usr/bin/afplay', '/System/Library/Sounds/Glass.aiff'],
                                capture_output=True, text=True, timeout=10)
        return {'player': 'afplay', 'exit_code': result.returncode,
                'error': result.stderr.strip()[:300] if result.returncode else None}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'player': 'afplay', 'exit_code': None, 'error': str(exc)[:300]}


def notify_once(track, state):
    receipt = OUT / 'notifications.json'
    saved = read(receipt, {'events': []})
    completion_id = state.get('completion_id')
    if not completion_id or state.get('state') not in TERMINAL:
        return False
    run_id = state.get('run_id', completion_id)
    key = track + ':' + run_id
    if any(x['key'] == key or (x['track'] == track and x.get('run_id') == run_id)
           for x in saved['events']):
        return False
    event = {'key': key, 'track': track, 'run_id': run_id,
             'state': state['state'], 'phase': state.get('phase'),
             'at': now(), 'sound': 'attempting'}
    saved['events'].append(event)
    write(receipt, saved)  # Durable notification identity; a restart cannot repeat the sound.
    event['sound'] = play_sound()
    write(receipt, saved)
    print(json.dumps(event), flush=True)
    return True


def watch(stop):
    while not stop.is_set():
        for track in TRACKS:
            try:
                notify_once(track, read(OUT / track / 'status.json'))
            except Exception as exc:
                print(f'Monitor notification error: {type(exc).__name__}: {exc}', flush=True)
        stop.wait(2)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'benchmarks'), **kwargs)

    def do_GET(self):
        route = urlsplit(self.path).path
        if route == '/api/status':
            try:
                body = json.dumps(snapshot(), ensure_ascii=False).encode()
                status = 200
            except Exception as exc:
                body = json.dumps({'error': str(exc)}).encode()
                status = 503
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if route == '/':
            self.path = '/parallel-search-20261006/monitor.html'
        return super().do_GET()

    def list_directory(self, path):
        self.send_error(403, 'Directory listing disabled; use the linked artifacts.')

    def log_message(self, fmt, *args):
        pass


def serve(port):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'monitor.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
        bound = server.server_address[1]
        write(OUT / 'monitor-process.json', {'pid': os.getpid(), 'started_at': now(),
              'url': f'http://127.0.0.1:{bound}/', 'sound': 'Glass.aiff',
              'mode': 'read-only status server; completion sounds; no paid submissions'})
        stop = threading.Event()
        worker = threading.Thread(target=watch, args=(stop,), daemon=True)
        worker.start()
        print(f'Monitor: http://127.0.0.1:{bound}/', flush=True)
        try:
            server.serve_forever()
        finally:
            stop.set()
            server.server_close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--test-sound', action='store_true')
    args = parser.parse_args()
    if args.test_sound:
        print(json.dumps(play_sound()))
    else:
        serve(args.port)
