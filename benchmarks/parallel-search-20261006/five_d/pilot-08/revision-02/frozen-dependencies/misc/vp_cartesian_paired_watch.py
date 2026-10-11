"""Read-only completion watcher for the frozen pilot08 paired confirmation.

Wait for every declared provider chunk before invoking the frozen analyzer.
No generation calls, retries, replacements, or final evaluation authorization.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import oai_batch_eval as io, vp_goal as runner
from misc.vp_cartesian_confirm_run import inspect


def watch(directory, manifest_paths):
    directory = Path(directory).resolve()
    manifest_paths = [Path(p).resolve() for p in manifest_paths]
    if len(manifest_paths) != 2:
        raise ValueError('Require both fixed provider manifests')
    manifests = [inspect(p) for p in manifest_paths]
    if {(m['provider'], m['fixed_n']) for m in manifests} != {('Anthropic', 2400), ('OpenAI', 240)}:
        raise ValueError('Unexpected paired pilot membership')
    fingerprints = {str(p): io.sha256(p) for p in manifest_paths}
    parts = [part for m in manifests for part in m['chunks']]
    if len({p['id'] for p in parts}) != len(parts):
        raise ValueError('Duplicate job IDs')
    declaration = directory / 'analysis-predeclaration.json'
    declared_hash = io.sha256(declaration)
    analyzer_module = io.read_json(declaration).get('analyzer_module', 'misc.vp_5d_analyze_08')
    if analyzer_module not in {'misc.vp_5d_analyze_08', 'misc.vp_5d_analyze_08_r1',
                               'misc.vp_5d_analyze_08_r2'}:
        raise ValueError('Unknown paired analyzer module')
    analyzer = ROOT / (analyzer_module.replace('.', '/') + '.py')
    analyzer_hash = io.sha256(analyzer)
    target = directory / 'aggregate-analysis.json'
    status_path = directory / 'analysis-watch.json'
    with (directory / 'analysis-watch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if target.exists():
            raise ValueError('Aggregate already exists; inspect its previous completion receipt')
        started = io.now()
        deadline = time.monotonic() + 26 * 3600
        while True:
            if any(io.sha256(Path(p)) != sha for p, sha in fingerprints.items()):
                raise ValueError('Fixed provider manifest changed')
            if io.sha256(declaration) != declared_hash or io.sha256(analyzer) != analyzer_hash:
                raise ValueError('Frozen analysis changed')
            state = runner.load()
            complete = 0
            for part in parts:
                job = state['jobs'].get(part['id'], {})
                if any(job.get(k) != part[k] for k in ('provider', 'phase', 'n', 'tasks_digest')):
                    raise ValueError('Registered job differs from its fixed declaration')
                complete += bool(job.get('settled') and job.get('collected_at'))
            record = {'pid': os.getpid(), 'started_at': started, 'updated_at': io.now(),
                      'manifest_sha256': fingerprints, 'analysis_declaration_sha256': declared_hash,
                      'settled_chunks': complete, 'required_chunks': len(parts),
                      'status': 'waiting_for_all_chunks', 'paid_calls': 0,
                      'final_authorization': False}
            if complete == len(parts):
                for p in manifest_paths:
                    inspect(p)
                with (directory / 'aggregate-analysis.log').open('a') as log:
                    subprocess.run([sys.executable, '-m', analyzer_module,
                                    'analyze', str(directory)], cwd=ROOT, stdout=log,
                                   stderr=subprocess.STDOUT, check=True)
                io.read_json(target)
                record.update(status='complete_pending_coordinator_review', aggregate_sha256=io.sha256(target))
                io.atomic_json(status_path, record)
                try:
                    sound = subprocess.run(['/usr/bin/afplay', '/System/Library/Sounds/Glass.aiff'],
                                           capture_output=True, text=True, timeout=10)
                    record['completion_sound_exit_code'] = sound.returncode
                except (OSError, subprocess.TimeoutExpired) as exc:
                    record['completion_sound_error'] = str(exc)
                io.atomic_json(status_path, record)
                subprocess.run([sys.executable, 'misc/vp_campaign_watch.py', '--refresh-only'],
                               cwd=ROOT, check=True)
                return record
            if (directory / 'analysis-watch.STOP').exists() or time.monotonic() >= deadline:
                record['status'] = 'stopped_incomplete'
                io.atomic_json(status_path, record)
                return record
            io.atomic_json(status_path, record)
            time.sleep(15)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('manifests', type=Path, nargs=2)
    args = parser.parse_args()
    try:
        print(json.dumps(watch(args.directory, args.manifests)))
    except Exception as exc:
        io.atomic_json(args.directory / 'analysis-watch.error.json',
                       {'at': io.now(), 'error': str(exc), 'paid_calls': 0})
        raise
