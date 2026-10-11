"""Input-only precision calculation. No task answers, provider calls, or ledger access."""
from __future__ import annotations
import itertools
import json
import math
from pathlib import Path


def bound(n, known_correct, *, references=2, joint_alpha=.05):
    if not (type(n) is int and n > 0 and type(known_correct) is int and 0 <= known_correct <= n):
        raise ValueError('Require a fixed positive denominator and a valid observed success count')
    alpha = joint_alpha / references
    margin = math.sqrt(math.log(1 / alpha) / (2 * n))
    lower = max(0., known_correct / n - margin)
    # Maximize p(1-p) over [lower,1]; no monotonicity assumption below one half.
    variance_upper = .25 if lower <= .5 else lower * (1 - lower)
    return dict(n=n, known_correct=known_correct, observed_known_correct_fraction=known_correct/n,
                per_reference_alpha=alpha, joint_alpha=joint_alpha, references=references,
                expected_accuracy_lower_bound=lower, hoeffding_margin=margin,
                fixed_panel_repeat_sd_upper=math.sqrt(variance_upper/n),
                interpretation='Conditional bound under independent calls and stable per-question probabilities; not new-root sampling uncertainty.')


def verify():
    """Exact small heterogeneous distributions check the claimed coverage and missingness direction."""
    scenarios = [(0., 0., 1., 1.), (.1, .4, .7, .95), (.8,) * 4,
                 (.02, .1, .5, .7, .9, .99)]
    evidence = []
    for probabilities in scenarios:
        n = len(probabilities)
        mean = sum(probabilities) / n
        variance = sum(p*(1-p) for p in probabilities) / n**2
        assert variance <= mean*(1-mean)/n + 1e-14
        for missing in [False, True]:
            failure_probability = 0.
            sd_undercoverage_probability = 0.
            for outcomes in itertools.product([0, 1], repeat=n):
                mass = math.prod(p if x else 1-p for p, x in zip(probabilities, outcomes))
                observed = sum(outcomes) - (outcomes[0] if missing else 0)
                b = bound(n, observed, references=1, joint_alpha=.2)
                failure_probability += mass * (b['expected_accuracy_lower_bound'] > mean + 1e-14)
                sd_undercoverage_probability += mass * (b['fixed_panel_repeat_sd_upper'] < math.sqrt(variance)-1e-14)
            assert failure_probability <= .2 + 1e-14
            assert sd_undercoverage_probability <= .2 + 1e-14
            evidence.append(dict(probabilities=probabilities, first_item_hidden=missing,
                mean_lower_bound_noncoverage=failure_probability,
                repeat_sd_upper_bound_noncoverage=sd_undercoverage_probability))
    assert bound(1800, 0)['fixed_panel_repeat_sd_upper'] == math.sqrt(.25/1800)
    assert bound(1800, 1433)['fixed_panel_repeat_sd_upper'] >= .01
    assert bound(1800, 1434)['fixed_panel_repeat_sd_upper'] < .01
    return evidence


if __name__ == '__main__':
    n = 1800
    out = dict(scope='Prospective methodological note; illustrative counts only, no final outcomes accessed.',
               final_scores_read=False, paid_calls=0, ledger_mutations=0, qualification_changed=False,
               fixed_n=n, joint_coverage_at_least=.95, reference_models=2,
               sufficient_known_correct_for_strict_sd_below_one_pp=1434,
               sufficient_known_correct_fraction=1434/n,
               illustrations={
                   'if_Opus_repeated_87.5_percent_development_rate': bound(n, 1575),
                   'if_Astra_repeated_80.5_percent_development_rate': bound(n, 1449)},
               exact_small_distribution_checks=verify())
    path = Path(__file__).with_name('audit.json')
    path.write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['illustrations','exact_small_distribution_checks']},indent=2))
