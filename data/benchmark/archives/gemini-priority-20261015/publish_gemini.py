"""Verify a finished Gemini run, archive execution evidence, publish six files.

Offline only. The archive contains every original file and can be extracted to
another directory for run_gemini.py verify. Never resend requests to regenerate
these reports.
"""
from collections import Counter
from copy import deepcopy
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation import run_gemini as runner
from data.engine.evaluation.scoring import score_output


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def desc(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': digest(path), 'bytes': path.stat().st_size}


def publish(folder):
    folder = folder.resolve()
    with (folder/'run.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest, tasks, _, validator = runner.load_inputs(folder)
        if manifest['status'] != 'completed' or manifest['execution']['pid'] is not None:
            raise RuntimeError('Only finished, stopped executions can be compacted')
        report = runner.inspect(folder, verify=True)
        if report['settled'] != 20000 or report['unresolved'] or report['not_started']:
            raise RuntimeError('Expected all 20000 settled tasks')
        refusals, incomplete = [], []
        for f in tasks:
            rows = json.loads((folder/f'{f}.json').read_bytes())
            validator.validate(rows)
            if [r['task_id'] for r in rows] != list(tasks[f]):
                raise RuntimeError('Source ordering or task coverage mismatch')
            for row in rows:
                if runner.transient_failure(row):
                    raise RuntimeError('Finish infrastructure recovery before publishing')
                expected = score_output(row['output_text'], tasks[f][row['task_id']]['gold_devanagari'], row['status'])
                if any(row[k] != v for k, v in expected.items()):
                    raise RuntimeError('Scoring mismatch')
                if row['status'] == 'refused':
                    refusals.append({'family': f, 'task_id': row['task_id'], 'error': row['error']})
                elif row['status'] != 'completed':
                    incomplete.append({'family': f, 'task_id': row['task_id'], 'status': row['status']})
        schema = json.loads((folder/'result.schema.json').read_bytes())
        original_files = sorted(p for p in folder.rglob('*') if p.is_file())
        if any(p.is_symlink() for p in folder.rglob('*')):
            raise RuntimeError('Unexpected symlink in execution directory')
        snapshot = {str(p.relative_to(folder)): desc(p) for p in original_files}
        archives = ROOT/'data/benchmark/archives'
        archives.mkdir(parents=True, exist_ok=True)
        archive = archives/f'{folder.name}-v3.tar.gz'
        temp = archive.with_suffix('.gz.tmp')
        if archive.exists() or temp.exists():
            raise RuntimeError('Archive already exists; inspect instead of overwriting')
        with tarfile.open(temp, 'w:gz', compresslevel=1) as tar:
            for rel in snapshot:
                tar.add(folder/rel, arcname=f'{folder.name}/{rel}', recursive=False)
        with tarfile.open(temp, 'r:gz') as tar:
            members = tar.getmembers()
            if {m.name for m in members} != {f'{folder.name}/{r}' for r in snapshot}:
                raise RuntimeError('Archive file list differs from original files')
            for member in members:
                if not member.isfile():
                    raise RuntimeError('Unexpected non-file archive member')
                with tar.extractfile(member) as stream:
                    actual = hashlib.file_digest(stream, 'sha256').hexdigest()
                rel = member.name.removeprefix(f'{folder.name}/')
                if actual != snapshot[rel]['sha256']:
                    raise RuntimeError(f'Archive changed bytes: {rel}')
        # Recheck every original after archive creation, before deleting anything.
        if any(digest(folder/rel) != entry['sha256'] for rel, entry in snapshot.items()):
            raise RuntimeError('Execution files changed while being archived')
        temp.replace(archive)
        compact = deepcopy(manifest)
        compact.update(artifact_layout='six-file-v1', summary=report,
                       result_schema={'storage': 'embedded', 'schema': schema,
                                      'original_file_sha256': snapshot['result.schema.json']['sha256']},
                       refusal_monitor={'checked_at': runner.base.now(), 'settled_results_scanned': 20000,
                                        'total_refusals': len(refusals), 'refusals': refusals,
                                        'other_noncompleted_results': incomplete,
                                        'meaning': 'Provider-reported promptFeedback blocks and candidate finish reasons; preserve all supplied safety ratings.'},
                       raw_run_archive={**desc(archive), 'member_root': folder.name,
                                        'contents': 'Complete original execution files: all request/response/error journals, original manifests/schema, results, logs and controls.'},
                       verification={'at': runner.base.now(), 'journal_replay': True, 'scoring': True,
                                     'schema': True, 'source_order': True, 'result_files': [desc(folder/f'{f}.json') for f in tasks],
                                     'archive_verified_against_every_original_file': True})
        compact['execution'].pop('concurrency_control_file', None)
        compact['execution']['resume'] = 'Completed compact export. Extract the raw archive into a separate directory to inspect or replay; do not resend completed requests.'
        compact['preservation']['public_layout'] = 'README.md, manifest.json, and four family result arrays. The embedded schema and raw archive replace execution sidecars.'
        compact['preservation']['execution_metadata'] = 'Journal paths in historical execution metadata are relative to the archived execution directory.'
        for entry in compact['tasks']:
            old_path = entry.pop('journal_file', f"journals/{entry['family']}.jsonl")
            archive_path = old_path+'.gz' if old_path+'.gz' in snapshot else old_path
            entry['journal_archive_member'] = f'{folder.name}/{archive_path}'
        compact['promotional_cost_estimate'] = {'gross_known_cost_usd': report['known_cost_usd'], 'estimated_cost_after_50_percent_credit_usd': round(report['known_cost_usd'] * .5, 8), 'meaning': 'Conditional estimate for October 2026 promotional eligibility; not confirmed billing credits or an invoice.'}
        correct = sum(f['correct'] for f in report['families'].values())
        strict = sum(f['strict_correct'] for f in report['families'].values())
        lines = [f"# {runner.MODELS[manifest['run_id']]['name']} — v3", '',
                 '20,000 tasks: 5,000 per family. Same sampled tasks and v3 templates as the Anthropic runs. HIGH thinking; no tools, web, history, maxOutputTokens or thinkingBudget parameters. The requested non-streaming v1 endpoint has a provider default of 32,768 output tokens including thinking.', '',
                 f"Exact-answer accuracy: **{correct/200:.3f}%** ({correct:,}/20,000). Answer plus required format: **{strict/200:.3f}%**. Provider refusals: **{len(refusals)}**.", '',
                 f"Gross cost before credits across all attempts: **${report['known_cost_usd']:.6f}**. Attempts with unknown final cost: **{report['unknown_cost_attempts']}**; these are not treated as free. Prices and reserves are in manifest.json.", '',
                 '| Task family | Correct | Exact accuracy | Answer + format |',
                 '|---|---:|---:|---:|']
        for f, stats in report['families'].items():
            lines.append(f"| {f} | {stats['correct']:,}/5,000 | {stats['correct']/50:.2f}% | {stats['strict_correct']/50:.2f}% |")
        lines += ['', 'The four family JSON files use the compact 13-field schema embedded in manifest.json. The manifest also pins datasets, templates, rates, API settings, code and verification hashes.', '',
                  f"The complete original execution is preserved in [the raw archive](../../archives/{archive.name}). Every archived file was checked against its original hash. Results were independently schema-validated, rescored and checked against journal replay and source ordering.", '',
                  'To audit, extract the archive into a separate directory and run `data/engine/evaluation/run_gemini.py verify --folder <extracted-run>`. This uses local journals and makes no API calls.', '']
        runner.base.atomic_write(folder/'README.md', '\n'.join(lines))
        runner.base.atomic_write(folder/'manifest.json', json.dumps(compact, ensure_ascii=False, indent=2)+'\n')
        keep = {'README.md', 'manifest.json', *(f'{f}.json' for f in tasks)}
        for rel in snapshot:
            if rel not in keep:
                (folder/rel).unlink()
        for directory in sorted((p for p in folder.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            directory.rmdir()
        if {p.name for p in folder.iterdir()} != keep:
            raise RuntimeError('Unexpected final directory layout')
        for f in tasks:
            if digest(folder/f'{f}.json') != snapshot[f'{f}.json']['sha256']:
                raise RuntimeError('Result bytes changed during compaction')
        return {'model': manifest['run_id'], 'tasks': report['settled'], 'correct': correct,
                'strict_correct': strict, 'cost_usd': report['known_cost_usd'], 'refusals': len(refusals),
                'archive': str(archive.relative_to(ROOT)), 'files': sorted(keep)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, required=True)
    print(json.dumps(publish(parser.parse_args().folder), indent=2))
