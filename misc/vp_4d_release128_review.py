"""Unpaid arithmetic/schedule review. Writes only the 4D review directory.

No provider clients, requests, result files, shared ledger mutations, or release
authorization. Costs are scenarios, not a promise of completion.
"""
from __future__ import annotations

import ast
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'benchmarks/parallel-search-20261006/four_d'
N = 4800
OA_BASE = 727_478_150
ANT_BASE = 188_615_334
PLANNED_ANT_CONFIRMATION_N = 2400
MICRO = 1_000_000


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def schedule():
    rows = []
    start = 0
    for end, size in [(3000, 100), (4000, 50), (4600, 25), (4800, 5)]:
        while start < end:
            stop = min(start + size, end)
            assert not start < 1000 < stop
            rows.append(dict(stage=len(rows) + 1, start_zero_based=start,
                             stop_exclusive=stop, n=stop - start,
                             phase='hard_final' if start < 1000 else 'hard_extension'))
            start = stop
    return rows


def scenario(stages, mean_micro, unit_max_micro):
    """Settle each predecessor at a fixed per-question cost, then max-reserve.

    This isolates liquidity. It is not a stochastic usage forecast, and does not
    spend reservations or assume they are receipts.
    """
    budget = 2_000_000_000 - OA_BASE
    balances = [Fraction(budget) - s['start_zero_based'] * mean_micro
                - s['n'] * unit_max_micro for s in stages]
    blocked = next((s for s, h in zip(stages, balances) if h < 0), None)
    return dict(mean_cost_usd=float(mean_micro / MICRO),
                projected_primary_cost_usd=float(N * mean_micro / MICRO),
                projected_lifetime_cost_usd=float((OA_BASE + N * mean_micro) / MICRO),
                expected_total_fits=(N * mean_micro <= budget),
                every_stage_reservable_under_constant_cost=blocked is None,
                first_blocked_stage=blocked,
                minimum_post_reservation_headroom_usd=float(min(balances) / MICRO),
                final_stage_post_reservation_headroom_usd=float(balances[-1] / MICRO))


def main():
    source = ROOT / 'misc/vp_goal.py'
    constants = {}
    for node in ast.parse(source.read_text()).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {'PROVIDERS', 'PHASES', 'INPUT_ALLOWANCE'}:
                    constants[target.id] = ast.literal_eval(node.value)
    providers = constants['PROVIDERS']
    assert providers['OpenAI']['cap_micro'] == 2_000_000_000
    assert providers['Anthropic']['cap_micro'] == 1_000_000_000
    allowance = constants['INPUT_ALLOWANCE']
    def maximum(provider, cap):
        p = providers[provider]
        return allowance * p['input_rate'] + cap * p['output_rate']
    oa_max = maximum('OpenAI', 128000)
    ant_old = maximum('Anthropic', 16384)
    ant_high = maximum('Anthropic', 128000)
    assert (oa_max, ant_old, ant_high) == (3_207_500, 166_840, 1_283_000)
    stages = schedule()
    assert len(stages) == 114
    assert sum(s['n'] for s in stages if s['phase'] == 'hard_final') == 1000
    assert sum(s['n'] for s in stages if s['phase'] == 'hard_extension') == 3800
    assert [i for s in stages for i in range(s['start_zero_based'], s['stop_exclusive'])] == list(range(N))
    assert [s['n'] for s in stages[-40:]] == [5] * 40

    # Whitelisted accounting only: no result files, answers or score fields.
    ledger_path = ROOT / 'benchmarks/iterative-goal-20261006/ledger.json'
    ledger_raw = ledger_path.read_bytes()
    state = json.loads(ledger_raw)
    diagnostic = state['jobs']['astra-five-d-cap-development-01']
    assert diagnostic['settled'] and diagnostic['n'] == 60
    diagnostic_cost = diagnostic['actual_cost_upper_micro']
    accounting = {}
    for provider in providers:
        jobs = [j for j in state['jobs'].values() if j['provider'] == provider]
        accounting[provider] = dict(
            settled_micro=state['historical_spend_micro'][provider] + sum(
                j.get('actual_cost_upper_micro', 0) for j in jobs if j.get('settled')),
            outstanding_max_micro=sum(j.get('reservation_micro', 0) for j in jobs if not j.get('settled')))
    mean = Fraction(diagnostic_cost, 60)
    uniform100 = [dict(stage=i // 100 + 1, start_zero_based=i,
                      stop_exclusive=i + 100, n=100,
                      phase='hard_final' if i < 1000 else 'hard_extension')
                  for i in range(0, N, 100)]
    taper_result = scenario(stages, mean, oa_max)
    uniform_result = scenario(uniform100, mean, oa_max)
    assert taper_result['every_stage_reservable_under_constant_cost']
    assert not uniform_result['every_stage_reservable_under_constant_cost']
    assert uniform_result['expected_total_fits']
    for cost in [Fraction(250000), Fraction(260000)]:
        assert scenario(stages, cost, oa_max)['every_stage_reservable_under_constant_cost']
    assert not scenario(stages, Fraction(263000), oa_max)['every_stage_reservable_under_constant_cost']
    oa_remaining = 2_000_000_000 - OA_BASE
    ant_after_worst_confirmation = 1_000_000_000 - ANT_BASE - PLANNED_ANT_CONFIRMATION_N * ant_old
    threshold = min(Fraction(oa_remaining - s['n'] * oa_max, s['start_zero_based'])
                    for s in stages if s['start_zero_based'])
    assert OA_BASE + 1000 * oa_max > 2_000_000_000  # Protection defeats any core split.
    report = dict(
        created_at=datetime.now(timezone.utc).isoformat(),
        status='offline_proposal_only_no_authorization',
        inputs=dict(parent_snapshot_settled_micro={'Anthropic': ANT_BASE, 'OpenAI': OA_BASE},
                    parent_planned_confirmation_n=PLANNED_ANT_CONFIRMATION_N,
                    accounting_snapshot_at=state['updated_at'],
                    accounting_snapshot=accounting,
                    ledger_sha256_at_snapshot=hashlib.sha256(ledger_raw).hexdigest(),
                    diagnostic_accounting_only=dict(n=60, cost_micro=diagnostic_cost,
                                                   mean_cost_usd=float(mean / MICRO))),
        reservation_per_question_usd=dict(OpenAI_128k=oa_max / MICRO,
                                         Anthropic_16384=ant_old / MICRO,
                                         Anthropic_128k=ant_high / MICRO),
        remaining_from_parent_snapshot_usd=dict(OpenAI=oa_remaining / MICRO,
                                                Anthropic_after_full_pending_max=ant_after_worst_confirmation / MICRO),
        full_release_worst_reservation_usd=dict(OpenAI_128k=N * oa_max / MICRO,
                                               Anthropic_16384=N * ant_old / MICRO,
                                               Anthropic_128k=N * ant_high / MICRO),
        maximum_guaranteed_count_from_remaining=dict(OpenAI_128k=oa_remaining // oa_max,
                                                    Anthropic_16384_after_confirmation=ant_after_worst_confirmation // ant_old,
                                                    Anthropic_128k_after_confirmation=ant_after_worst_confirmation // ant_high),
        total_cost_affordability_ceiling_mean_usd=oa_remaining / N / MICRO,
        taper_prefix_constant_mean_ceiling_usd=float(threshold / MICRO),
        proposed_schedule=stages,
        size_counts=dict(Counter(s['n'] for s in stages)),
        final_stage_max_reservation_usd=5 * oa_max / MICRO,
        scenario_diagnostic_mean=taper_result,
        scenario_uniform_100=uniform_result,
        scenario_sensitivity=[scenario(stages, Fraction(x), oa_max) for x in [240000, 250000, 260000, 263000]],
        tests_passed=['exact_4800_ordered_partition', 'exact_first_1000_core',
                      'max_reservations_use_fixed_rates', 'default_128k_core_protection_blocks',
                      'uniform100_can_block_when_total_expected_cost_fits',
                      'taper_finishes_at_diagnostic_mean_and_025_026_constant_cost',
                      'taper_still_can_block_at_0263_despite_total_fitting'],
        invariants=dict(no_provider_clients=True, no_model_answer_access=True,
                        no_shared_mutations=True, no_release_authorization=True),
        dependencies={str(p.relative_to(ROOT)): sha(p) for p in [source,
                      ROOT / 'misc/vp_cartesian_release.py',
                      ROOT / 'misc/vp_cartesian_release_run.py', Path(__file__)]})
    path = OUT / 'release128-operational-review-01.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['reservation_per_question_usd',
        'remaining_from_parent_snapshot_usd','maximum_guaranteed_count_from_remaining',
        'total_cost_affordability_ceiling_mean_usd','taper_prefix_constant_mean_ceiling_usd',
        'scenario_diagnostic_mean','scenario_uniform_100','tests_passed']}, indent=2))


if __name__ == '__main__':
    main()
