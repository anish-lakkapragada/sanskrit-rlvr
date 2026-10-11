"""Offline previews of source-backed input repairs; never change an evaluated task."""
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'pyproject.toml').exists())
sys.path.insert(0, str(ROOT))
from finetune.prompts import slp1_to_devanagari
from misc.vp_cartesian_prompt_v1 import render
from vidyut.prakriya import Dhatu, Gana, Lakara, Pada, Prayoga, Purusha, Vacana, Vyakarana


def read(path):
    return json.loads(path.read_text())


def fingerprint(path):
    return {'path': str(path.relative_to(ROOT)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    candidate = HERE.parents[2] / 'candidate-1800-v1'
    # HERE = source-adjudication; parents[2] is four_d-90.
    tasks_path = candidate / 'tasks.json'
    prompts_path = candidate / 'public-prompts.json'
    tasks = read(tasks_path)
    prompts = {t['id']: t['prompt'] for t in read(prompts_path)}
    docs = [HERE / 'lexical-holds-followup.json', HERE / 'shared-holds-followup.json']
    cases = {row['index']: row for doc in docs for row in read(doc)['rows']}
    before = [fingerprint(p) for p in [tasks_path, prompts_path, *docs]]
    rows = []
    grammar = Vyakarana()
    for index in (437, 481, 495):
        original = tasks[index]
        assert cases[index]['task_id'] == original['id']
        assert render(original) == prompts[original['id']]
        assert '\\' not in original['dhatu']['aupadeshika']
        proposed = copy.deepcopy(original)
        proposed['dhatu']['aupadeshika'] += '\\'
        dhatu, m = proposed['dhatu'], proposed['morphology']
        variants = grammar.derive(Pada.Tinanta(
            dhatu=Dhatu.mula(dhatu['aupadeshika'], getattr(Gana, dhatu['gana'])),
            lakara=getattr(Lakara, m['lakara']), prayoga=getattr(Prayoga, m['prayoga']),
            purusha=getattr(Purusha, m['purusha']), vacana=getattr(Vacana, m['vacana'])))
        engine = sorted({slp1_to_devanagari(p.text) for p in variants})
        source = sorted(set(engine) | ({'जम्भते'} if index == 437 else set()))
        expected = {437: ['जभते', 'जम्भते'], 481: ['अरेबामहि'], 495: ['खुण्डिताध्वे']}[index]
        assert source == sorted(expected)
        assert not set(source) & set(original['gold_devanagari'])
        old_visible = slp1_to_devanagari(original['dhatu']['aupadeshika'])
        new_visible = slp1_to_devanagari(dhatu['aupadeshika'])
        prompt = render(proposed)
        assert prompt == prompts[original['id']].replace(old_visible, new_visible)
        rows.append({
            'historical_index': index, 'historical_task_id': original['id'],
            'historical_prompt_sha256': original['campaign']['prompt_sha256'],
            'old_dhatu': original['dhatu'], 'proposed_dhatu': dhatu,
            'unchanged_four_coordinates': m,
            'proposed_prompt': prompt,
            'proposed_prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
            'old_gold_devanagari': original['gold_devanagari'],
            'engine_regenerated_gold_devanagari': engine,
            'source_supported_proposed_gold_devanagari': source,
            'source_only_additions': sorted(set(source) - set(engine)),
            'source_limits': ('The nonnasal jabh form is an attributed printed Kshira reading; '
                              'the nasal form has a positive num derivation. This is not an optional-num claim.'
                              if index == 437 else 'Ending set follows the independently sourced middle entry.'),
            'new_provider_responses': 0,
            'new_identity_and_registration_required_before_any_submission': True,
        })
    assert before == [fingerprint(p) for p in [tasks_path, prompts_path, *docs]]
    result = {
        'schema': 'source-backed-input-repair-previews-v1',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'status': 'preview_only_not_registered_not_evaluated',
        'rows': rows, 'input_fingerprints': before,
        'same_task_shape': 'Dictionary dhatu plus lakara, prayoga, purusha, vacana. No new coordinate.',
        'policy': 'Historical inputs, answers and grades remain unchanged. Old responses are not responses to these repaired prompts.',
        'no_outcome_membership_filtering': True, 'paid_calls': 0,
        'benchmark_ready': False,
    }
    out = HERE / 'input-repair-previews.json'
    assert not out.exists(), 'Preserve the first repair preview; create a new version for revisions.'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(out.relative_to(ROOT)), 'repairs': len(rows),
                      'historical_mutations': 0, 'paid_calls': 0}, indent=2))


if __name__ == '__main__':
    main()
