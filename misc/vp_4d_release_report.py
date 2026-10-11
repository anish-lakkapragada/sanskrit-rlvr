#!/usr/bin/env python3
"""Render the aggregate release-feasibility report without changing membership."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc.vp_4d_pilot import OUT, write, now


def main():
    path = OUT / 'release-feasibility-01.json'
    data = json.loads(path.read_text())
    review = json.loads((OUT / 'pilot-01.disagreement-review.json').read_text())
    by_case = {(a['n'], a['family_cap']): a for a in data['allocations']}
    primary = [by_case[1000,3], by_case[1601,5]]
    names = {
        'internal_rv_lengthening':'Internal r/v lengthening',
        'svadi_perfect':'Svadi perfect',
        'other_athematic_perfect':'Other athematic perfect',
        'perfect_reduplication_changes':'Perfect reduplication changes',
        'divadi_sigmatic_aorist':'Divadi sigmatic aorist',
        'aorist_consonant_changes':'Aorist consonant changes',
        'athematic_present_system':'Athematic present system',
        'dictionary_curadi_futures':'Dictionary Curadi futures',
        'transitive_curadi_nonpresent_passive':'Transitive Curadi nonpresent passive',
        'primary_benedictive_stem_changes':'Primary benedictive stem changes',
    }
    lines = ['# 4D release feasibility 01', '',
        'Both required sizes have feasible aggregate allocations after grammatical quarantine: **1,000 questions with at most three per family**, and **1,601 with at most five per family**, each using **464 master-test families**. This establishes supply and diversity feasibility only. The observed Opus pilot remains too easy, and neither model accuracy nor sub-one-point standard error is established for a release.', '',
        'No final task IDs or membership lists were emitted. The optimizer used capacities of grammar bins, stripped of root code, dictionary text, task IDs, and surface forms. Test model answers and test gold forms were not loaded. The master development/test/RL assignments are unchanged. The old 500/500 test suballocation is not imposed on these calculations.', '',
        '## Scope and allocation constraints', '',
        'Every hypothetical task remains a dictionary dhatu plus exactly lakara, prayoga, purusha, and vacana. There are no added derivations, prefixes, or independently selected padas. Passive questions use the pilot’s exact transitive-meaning allowlist. All ten pilot grammar predicates are retained.', '',
        'The common feasibility constraints require all ten classical lakaras (each at least 3%, at most 25%), all ten ganas (at least one task each, at most 30%), each person and number between 20% and 40%, passive between 3% and 15%, and each grammar cell between 2% and 25%. The family maximum is varied as a diagnostic; it is not a user-mandated ceiling. The objective preserves pilot proportions where feasible, then spreads tasks across families. Pilot scores are not optimization inputs.', '',
        'The screened predicate union contains **11,650 unique model-visible tuples across 464 families**. Overlapping cells share capacity constraints, preventing double counting. Integer witnesses were checked independently against all capacity and diversity constraints. HiGHS 1.15.1 solved each reported case.', '',
        '## Feasible compositions', '',
        '| Grammar cell | N = 1,000, max 3/family | N = 1,601, max 5/family |',
        '|---|---:|---:|']
    for label, name in names.items():
        lines.append(f'| {name} | {primary[0]["cells"][label]} | {primary[1]["cells"][label]} |')
    lines += ['', '| Diagnostic | N = 1,000 | N = 1,601 |', '|---|---:|---:|']
    for label, key, fmt in [('Families','root_families','d'),('Maximum tasks per family','max_tasks_per_family','d'),
                            ('Maximum family share','max_family_fraction','percent'),('Maximum lakara share','max_lakara_fraction','percent'),
                            ('Maximum gana share','max_gana_fraction','percent')]:
        values = [f'{a[key]*100:.3f}%' if fmt=='percent' else str(a[key]) for a in primary]
        lines.append(f'| {label} | {values[0]} | {values[1]} |')
    for a in primary:
        hist = ', '.join(f'{k} tasks: {v} families' for k,v in a['family_size_histogram'].items())
        lines += ['', f'For N={a["n"]:,}, the family-size histogram is {hist}.',
                  'Lakara counts: ' + '; '.join(f'{k} {v}' for k,v in a['distributions']['lakara'].items()) + '.',
                  'Gana counts: ' + '; '.join(f'{k} {v}' for k,v in a['distributions']['gana'].items()) + '.']
    lines += ['', 'All person, number, voice, and cell distributions are in the JSON artifact. These are examples of feasible compositions, not recommended final weights.', '',
        'Two tasks per family cannot supply 1,000 questions under the proposed gana limit. Four per family cannot supply 1,601. These lower bounds follow from summed family capacities capped by gana, independently of the solver; the feasible witnesses show that maxima of three and five, respectively, suffice.', '',
        '## Narrow-cell limits', '',
        'The full master test split has only nine internal-lengthening families, 14 Svadi-perfect families, and 15 families in the narrow transitive Curadi passive cell. Their upper capacities at a common family maximum K are:', '',
        '| K | Lengthening | Svadi perfect | Narrow passive |', '|---:|---:|---:|---:|']
    for k in [3,5,6,8,10]:
        lines.append(f'| {k} | {9*k} | {min(14*k,126)} | {min(15*k,270)} |')
    lines += ['', 'These individual upper bounds need not be jointly attainable because families and grammar cells overlap. The reported integer allocations account for that overlap. Increasing the family maximum increases narrow-cell weight but does not create new independent families.', '',
        '## Precision and family dependence', '',
        'For an illustrative exchangeable within-family correlation ρ, independent families, common accuracy p, and m_f tasks in family f, the variance of the unweighted accuracy is:', '',
        '`Var(accuracy) = p(1-p)/N × [1 + ρ × (Σ m_f²/N − 1)]`', '',
        'The bracket is the design effect. This is a sensitivity model, not an estimated correlation or a precision certificate. Here is SE in percentage points at p=0.80:', '',
        '| Feasible N / family maximum | ρ = 0 | ρ = .02 | ρ = .05 | ρ = .10 | ρ = .20 |',
        '|---|---:|---:|---:|---:|---:|']
    for key in [(1000,3),(1601,5),(2000,8),(2400,10)]:
        a=by_case[key]
        values=' | '.join(f'{x["se_at_80_percent_in_percentage_points"]:.4f}' for x in a['uncertainty_sensitivity'])
        lines.append(f'| {key[0]:,} / {key[1]} | {values} |')
    threshold=primary[1]['maximum_positive_icc_compatible_with_se_strictly_below_one_point']
    lines += ['', f'For the 1,601-task witness, SE is below one point only for ρ below approximately **{threshold:.6f}** under these assumptions. That is effectively an independence requirement. At accuracy 79%, even 1,601 independent tasks miss the one-point threshold: at least 1,660 are required. The 2,400-task sensitivity case also has almost no margin at ρ=.10 and p=.80; near 79% it exceeds one point.', '',
        'More tasks within the same 464 families have diminishing precision returns. The JSON includes sum-of-squared family counts and effective family counts for every scenario. Exact-citation-plus-gana grouping can also split related lexical roots across families, so dependence may extend beyond the declared groups.', '',
        'Before final evaluation, freeze an extension rule tied to a prespecified family-aware SE estimator, maximum authorized size, and shared budget. Report family-cluster uncertainty and a sensitivity analysis for related-root grouping. Do not choose an extension because the observed score is outside 79–81%; that would adapt membership to the score target. The current work does not alter the coordinator’s budget or reserve.', '',
        '## Development results and validity review', '',
        '**Opus 5.5 xHigh/16,384 scored 108/120 overall and 108/118 usable answers (91.53%)**, with two refusals and no truncations. The exploratory family-cluster ratio SE is about 3.02 points. The coordinator records a $0.6912 upper cost for this job. This worker made no paid calls or ledger changes.', '',
        'Five of ten exact-answer misses are internal vowel-lengthening errors concentrated in three root families. The broad present-system, other athematic perfect, perfect-reduplication, aorist-consonant, and primary-benedictive cells scored 100% in this small pilot. The passive cell had two refusals and 10/10 correct usable answers; refusals provide no evidence of grammatical hardness.', '',
        'Two remaining scored misses reveal strong oracle concerns, so the raw score is preserved and the contexts are quarantined rather than used to increase difficulty:', '',
        '- **Svadi rādh, meaning saṃsiddhau:** VP applies 6.4.123 and accepts रेध, while the model supplied रराध. The [primary commentary](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.123.htm) restricts the reduction to the injuring sense and contrasts unreduced forms otherwise. Upstream code checks the gana without a semantic condition and includes a TODO. Exclude these rule contexts pending certification.',
        '- **Divadi ñitṛṣā̃ aorist:** dictionary `YitfzA~` differs from the hard-coded PUSH_ADI string `Yitfza~`. A local marker-only reproduction switches VP from the scored sigmatic form to the model’s अतृषाव and activates [3.1.55](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.55.htm). The [primary Dhatupatha](https://sa.wikisource.org/wiki/अष्टाध्यायी-धातुपाठः) places this root in puṣādi. A score-independent list audit also found `04.0113 yusa~` absent from the list; its test-family aorists are conservatively excluded without reading any test answers.', '',
        'The putha aorist disagreement is different: that root occurs before puṣādi in the primary Dhatupatha, supporting the engine’s sigmatic analysis. The two Curadi future/conditional errors concern dictionary Akusmiya roots for which the model chose Parasmaipada. [Dhatupatha and Dhatupradipa evidence](https://jainqq.org/booktext/Dhatupradip/004319) supports an Atmanepada subgroup; exact variant entries still deserve direct review before this becomes a sampling lead.', '',
        'The Data loader also silently attaches prefixes to dictionary entries 02.0012, 02.0041, 02.0042, and 10.0368. None occurs in the pilot. All inherited-prefix or inherited-sanadi entries are excluded from the revised feasibility census. The three affected master-test families and one missing-list aorist family reduce the original union from 468 to 464 families. Master split membership is unchanged.', '',
        'A coordinated passive audit found no pilot overlap with the missing optional Cinvat lengthening reported by the 5D worker: all 12 4D passives have rule 6.4.62, but none has 6.4.92. The future exclusion checks both rules across all nonpresent passive lakaras, including the benedictive. It removes zero current master-test candidate rows. The [primary commentary on 6.4.62](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.62.htm) documents the relevant causal-passive long and short alternatives; this targeted diagnostic is not complete passive-key certification.', '',
        'A dictionary-only audit also found four pairs with identical visible citation, gana, and meaning but different intrinsic antargana metadata: jvala, cala, dhvana, and arha. None appears in this pilot or the current master-test predicate union. Future generation must use a complete audited union for indistinguishable entries or quarantine them; a hidden dictionary code must not select a narrower answer key. The feasibility code now quarantines these identities, with zero additional supply impact.', '',
        'These exclusions were developed after development-result discovery and are explicitly recorded as such. The frozen pilot, raw gold, raw responses, and historical headline score are untouched. Omitting the two contested usable questions gives a diagnostic 108/116 (93.10%), reinforcing that this mixture is too easy; it is not a revised certified benchmark score.', '',
        '## Next useful experiment', '',
        'The only new bounded lead supported by this pilot is the lexical Atmanepada restriction of the Akusmiya subgroup. There are 17 development, 18 test, and 10 RL-training families. Both of the pilot’s Akusmiya active questions failed, but two examples cannot estimate subgroup difficulty. A fresh development probe across tenses and persons could test the mechanism after direct variant-entry audit. It would remain exactly 4D: the ending restriction is a property of the dictionary root, not an added coordinate.', '',
        'A proposal is recorded in `next-experiment-proposal-02.json`, explicitly non-submittable until questions and lexical audits are prepared. No new paid request has been submitted. Even if the lead works, its small family supply and the maximum Curadi concentration must be considered before fitting final weights. Current results do not justify an Astra replication of an already-too-easy aggregate merely to seek 80%.', '',
        '## Reproduction and artifacts', '',
        '- `misc/vp_4d_release_feasibility.py`: reads grammar metadata, aggregates capacities, solves and validates allocations, emits only aggregate results.',
        '- `release-feasibility-01.json`: all eight allocation cases, capacity bounds, distributions and uncertainty sensitivities.',
        '- `release-feasibility-01.before-grammar-quarantine.json`: preserved initial calculation before validity findings.',
        '- `pilot-01.disagreement-review.json`: raw development scores and per-disagreement audit classifications.',
        '- `pilot-01.oracle-evidence.json` and `misc/vp_4d_oracle_evidence.py`: reproducible citation-only diagnostic, passive cross-check, and visible-identity audit.',
        '- `pilot-01.scope-audit.json`: all 120 tasks regenerate, with 120 unique prompts and no inherited operations; this is not full oracle certification.',
        '- `misc/vp_4d_release_report.py`: renders this report.', '',
        'The solver dependency is scoped to this worker’s artifact folder; the shared Python environment is unchanged. Recreate it with `uv pip install --target benchmarks/parallel-search-20261006/four_d/_solver_deps --no-deps highspy==1.15.1`, then run the two worker scripts with `.venv/bin/python`.']
    (OUT/'release-feasibility-01.md').write_text('\n'.join(lines)+'\n')
    data['development_pilot_summary']=review['raw_scores']
    data['disagreement_review_path']='pilot-01.disagreement-review.json'
    data['final_membership_frozen']=False
    data['benchmark_ready']=False
    data['report_generated_at']=now()
    write(path,data)


if __name__ == '__main__':
    main()
