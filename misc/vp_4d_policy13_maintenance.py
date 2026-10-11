#!/usr/bin/env python3
"""Offline policy13 frontier refresh; preserves completed-run status and old artifacts."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import vp_4d_mixture_frontier as frontier
from misc.vp_4d_pilot import OUT, now, sha, write


def main():
    target = OUT / 'pilot-04.mixture-frontier-r3-policy13.json'
    if target.exists():
        raise SystemExit('Preserve the existing maintenance frontier; use a new version.')
    previous = json.loads((OUT / 'pilot-04.mixture-frontier-r2.json').read_text())
    original_status = json.loads((OUT / 'status.json').read_text())
    frontier.status = lambda *args: None

    def save(path, data):
        assert Path(path).name == 'pilot-04.mixture-frontier-r2.json'
        data['revision'] = 'Policy13 maintenance; preserve r2 and completed run identity. Exact svid lexical quarantine removes one correct pilot03 development answer. The unresolved-stim sensitivity baseline changes from 175/175 to 174/174, leaving its numerical rate unchanged.'
        data['reference_details']['background03'] = '174/174 after policy13 and sensitivity omission of the unresolved stim disagreement. The ordinary current-policy pilot03 score is 174/175. This is a point estimate, not certainty or an independent measurement.'
        data['maintenance'] = True
        data['shared_policy'] = 'oracle-policy-13.json'
        data['maintenance_script_sha256'] = sha(__file__)
        data['previous_frontier_sha256'] = sha(OUT / 'pilot-04.mixture-frontier-r2.json')
        diffs = []
        for before, after in zip(previous['results'], data['results'], strict=True):
            for key in ['n', 'family_cap', 'curadi_share_cap', 'spread_floors', 'five_classes_at_least_five_percent', 'evidence_model', 'status']:
                assert before[key] == after[key]
            delta = after.get('optimistic_accuracy_bound', 0) - before.get('optimistic_accuracy_bound', 0)
            if abs(delta) > 1e-10:
                diffs.append(dict(n=after['n'], evidence_model=after['evidence_model'], delta=delta))
        data['policy13_impact'] = dict(
            supply_unchanged=previous['supply'] == data['supply'],
            total_test_metadata_tuples_before=previous['total_test_metadata_tuples'],
            total_test_metadata_tuples_after=data['total_test_metadata_tuples'],
            total_test_families_before=previous['total_test_families'],
            total_test_families_after=data['total_test_families'],
            weighted_rate_changes=diffs,
            interpretation='The excluded exact svid entry belongs to development, but removing it also changes marker-contrast eligibility for its test counterpart. The refreshed capacity delta is reported separately from the unchanged numerical rates. Policy13 nested-derivation predicates do not apply to exact4D.',
        )
        print('Maintenance capacity comparison:', data['policy13_impact'])
        print('Previous supply:', previous['supply'])
        print('Current supply:', data['supply'])
        write(target, data)

    frontier.write = save
    frontier.main()
    assert json.loads((OUT / 'status.json').read_text()) == original_status
    print('Policy13 maintenance: refreshed test capacities and compared all weighted rates; completed status untouched.')


if __name__ == '__main__':
    main()
