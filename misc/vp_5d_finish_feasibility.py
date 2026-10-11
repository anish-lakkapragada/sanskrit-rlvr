"""Assemble the bounded offline assessment; never choose release membership."""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from misc.vp_5d_pilot import OUT,RECIPES,atomic_json,now,sha


def main():
    analysis=json.loads((OUT/'release-feasibility-01.reviewed-analysis.json').read_text())
    pilot=json.loads((OUT/'pilot-01.result-review.json').read_text())
    supply=json.loads((OUT/'release-feasibility-01.reviewed-supply.json').read_text())
    hidden=json.loads((OUT/'pilot-01.hidden-modifier-audit.json').read_text())
    passive=json.loads((OUT/'release-feasibility-01.passive-oracle-review.json').read_text())
    adjusted=[x for x in analysis['diversity_optimized_checks'] if x['quota_mode']=='supply_adjusted_gana']
    precision=[]
    for x in analysis['diversity_optimized_checks']:
        precision.append({'n':x['n'],'quota_mode':x['quota_mode'],
            'family_count':x['maximum_distinct_families'],
            'family_load_histogram':x['family_load_histogram'],
            'design_effect_formula':'1 + (sum(m_f^2)/N - 1) * rho',
            'within_family_pair_multiplier':x['family_pair_correlation_multiplier'],
            'se_percentage_points_at_p_80':{str(r):100*math.sqrt(.16/x['n']*(1+r*x['family_pair_correlation_multiplier'])) for r in [0,.05,.1,.2,.5,1]}})
    baseline=OUT/'release-feasibility-01.pre-audit-analysis.json'
    if not baseline.exists():
        baseline.write_bytes((OUT/'release-feasibility-01.json').read_bytes())
    analysis['created_at']=now()
    analysis['state']='bounded_offline_assessment_complete'
    analysis['run_id']='release-feasibility-01'
    analysis['grammar_filters']={
        'coordinates':['lakara','prayoga','purusha','vacana','derivation_recipe'],
        'recipe_menu':{r:s['sanadi'] for r,s in RECIPES.items()},
        'prefixes':False,'independent_pada':False,'dictionary_hidden_modifiers':False,
        'intensive_lexical_scope':'Consonant-initial normalized root with exactly one vowel; no Curadi, roch or shobh; semantic conditions inherent in the traditional intensive operation.',
        'nested_excluded_rule_ids':['7.4.79','7.4.80','7.4.94','7.4.95','8.3.61'],
        'passive_scope':'Causal recipes only, in Lat, Lan, Lot, VidhiLin, Lut and Lrt.',
        'new_passive_exclusion':passive['prospective_exclusion'],
        'maximum_engine_variants':64,'nonempty_engine_derivation_required':True}
    analysis['development_evidence']={k:pilot[k] for k in [
        'experiment','reference','n','completed','correct_completed','completed_exact_accuracy',
        'all_request_accuracy','refused','truncated','infrastructure_failures','completed_iid_se',
        'completed_wilson_95','cells','error_categories','confirmed_oracle_corrections',
        'oracle_completeness_issue','raw_scores_unchanged','paid_cost_upper_usd_from_coordinator_record']}
    analysis['development_evidence']['used_for_release_supply_membership']=False
    analysis['development_evidence']['weights_changed_from_pilot']=False
    analysis['development_evidence']['held_out_model_answers_read']=False
    analysis['design_specific_precision_sensitivity']=precision
    analysis['independent_precision_thresholds']={
        'strictly_below_one_percentage_point_se_at_p_80':1601,
        'strictly_below_one_percentage_point_se_at_p_79':1660,
        'explanation':'The nominal 1,601 threshold uses exactly p = .80. At p = .79, the larger Bernoulli variance needs at least 1,660 independent questions. Dependence can require more.'}
    analysis['recommended_capacity_tradeoff']={
        'status':'Proposal only; not frozen sampling or membership.',
        'max_tasks_per_family':2,'quota_mode':'supply_adjusted_gana',
        'sizes_assessed':[1000,1601],'all_ten_ganas':True,
        'results':[{k:x[k] for k in ['n','maximum_distinct_families','family_load_histogram','gana_counts','max_gana_fraction','balanced_person_number_counts']} for x in adjusted],
        'reason':'Keeps all ten classes and broad tense/recipe coverage while reducing repeat-family dependence relative to exact pilot class weights.'}
    analysis['split_policy']={
        'development_families':700,'master_test_families':1000,'rl_training_families':462,
        'eligible_test_families_after_modifier_filter':997,
        'legacy_500_500_suballocation':'Unchanged by worker; coordinator may supersede it before final exposure.',
        'final_membership_frozen':False,'task_ids_or_gold_exported_from_test_pool':False}
    analysis['source_evidence']={
        'initial_direct_source_control_count':8,
        'new_direct_passive_control_count':len(passive['source_checks']),
        'new_control_contexts_missing_documented_forms':sum(bool(x['missing_source_forms']) for x in passive['source_checks']),
        'direct_sources':['https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.62.htm','https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.93.htm'],
        'nested_composition_limits':'jF/JF short-i ordering and lih vowel preservation are source-supported inference or analogy, not direct examples of those complete forms. Nested passive licensing is compositional; the direct examples do not certify every complete nested passive chain.'}
    analysis['artifacts']={name:sha(OUT/name) for name in [
        'release-feasibility-01.reviewed-supply.json','release-feasibility-01.passive-oracle-review.json',
        'pilot-01.result-review.json','pilot-01.hidden-modifier-audit.json','pilot-01.post-modifier-runner-audit.json']}
    analysis['completion_limits']=[
        'No strongest-reference 79–81% benchmark established. Opus completed accuracy is 85.22%; Astra is unmeasured.',
        'Final task membership, RL examples and reference evaluation remain outstanding.',
        'Mechanical feasibility is not independent grammatical certification.',
        '1,601 tasks barely meets the independent-binomial precision threshold at exactly 80%; positive family correlation can invalidate that threshold.',
        'No new paid request should execute before the coordinator resolves the documented oracle scope.']
    atomic_json(OUT/'release-feasibility-01.json',analysis)

    request={'created_at':now(),'track':'five_d','run_id':'release-feasibility-01',
        'status':'hold_pending_oracle_scope_resolution','submitted':False,'spending_authorized_by_worker':False,
        'kind':'next_step_recommendation','task_file':None,
        'reference_order':['Opus 5.5','GPT-6 Astra'],'reasoning_effort':'xhigh','max_output_tokens':16384,
        'rationale':'The completed-answer Opus estimate is above target; a fresh panel is warranted only after the incomplete passive context is excluded or independently repaired. Recipe-specific estimates are small and Astra may be stronger.',
        'required_offline_steps':[
            'Adopt an explicit prospective exclusion of Karmani Lut/Lrt traces containing both 6.4.62 and 6.4.92, or repair and independently audit every documented variant.',
            'Keep original pilot answers and scores immutable; do not report its refusal-inclusive rate as grammatical accuracy.',
            'Review the three inference-supported nested forms and retain their evidence labels.',
            'For any subsequent paid panel, generate fresh development tasks under the adopted filters, freeze its file hash and distribution, and run the shared full validator.'],
        'suggested_experiment_after_resolution':{
            'phase':'Fresh broad development calibration','maximum_questions':120,
            'providers':['Anthropic','OpenAI'],'same_questions_for_references':True,
            'distribution_policy':'Keep broad lakara and class coverage. Treat intensive_luk and causative_of_intensive as hypotheses for moderate weight increases, not as proven 80% recipes; no new weights are fixed here.',
            'adapter_needs':'Existing cartesian_5d adapter suffices; prospective grammar checks must run before generating the frozen file.'},
        'release_size_recommendation':'Assess at least 1,601 tasks if precision below one percentage point remains mandatory; predeclare any larger extension before final answers. Estimate cluster uncertainty by family.',
        'budget_owner':'Coordinator only; no ledger mutation or paid worker call.'}
    atomic_json(OUT/'release-feasibility-01.next-step-request.json',request)

    recipe_rows='\n'.join(f"| `{r}` | {v['families']:,} | {v['tuples']:,} |" for r,v in analysis['recipes'].items())
    labels={'exact_pilot_gana':'Pilot class proportions','relaxed_gana':'Unconstrained classes','supply_adjusted_gana':'Supply-adjusted classes'}
    capacity_rows='\n'.join(f"| {x['n']:,} | {labels[x['quota_mode']]} | {x['max_per_family']} | {x['maximum_distinct_families']:,} | {100*x['max_gana_fraction']:.2f}% |" for x in analysis['diversity_optimized_checks'])
    class_rows='\n'.join(f"| {g} | {analysis['eligible_family_gana'][g]} | {adjusted[0]['gana_counts'][g]} | {adjusted[1]['gana_counts'][g]} |" for g in analysis['family_gana'])
    score_rows='\n'.join(f"| `{r}` | {v['correct']}/{v['completed']} | {100*v['completed_exact_accuracy']:.2f}% | {v.get('refused',0)} |" for r,v in pilot['cells'].items())
    se_rows='\n'.join(f"| {x['n']:,} | {labels[x['quota_mode']]} | {x['se_percentage_points_at_p_80']['0']:.4f} | {x['se_percentage_points_at_p_80']['0.05']:.4f} | {x['se_percentage_points_at_p_80']['0.1']:.4f} | {x['se_percentage_points_at_p_80']['0.2']:.4f} |" for x in precision if x['quota_mode']!='relaxed_gana')
    report=f'''# Isolated 5D release feasibility 01

This bounded offline assessment supports **1,000 or 1,601 distinct questions with at most two questions per family**, all ten classes and broad tense coverage after the declared grammar exclusions. It does **not** establish the 79–81% strongest-reference target or certify every oracle form. Opus scored **98/115 completed answers, 85.22%**, with five refusals. No Astra result is available.

No final membership was selected or exported, no held-out model answers were read, and no paid calls or shared-ledger writes were made by this worker. The full 1,000-family master test pool was used only for the coordinator-authorized availability census. The old 500/500 suballocation and development/test/RL family assignments remain unchanged.

## Grammar scope and reviewed supply

The dictionary dhatu has exactly four inflection coordinates plus one fixed-menu ordered sanadi recipe. Prefixes, extra pada choices, nominal outputs and additional semantic choices are absent. The six recipes remain `[Ric]`, `[san]`, `[yaN]`, `[yaNluk]`, `[yaN, Ric]` and `[yaN, Ric, san]`. All ten classical lakaras and all nine person-number pairs are counted. Karmani is limited to causal recipes in Lat, Lan, Lot, VidhiLin, Lut and Lrt.

The intensive filter requires a consonant-initial normalized root with one vowel, excludes Curadi and the specified roch/shobh nonusage, and retains the traditional operation's lexical semantic restrictions. Nested recipes exclude traces of 7.4.79, 7.4.80, 7.4.94, 7.4.95 and 8.3.61. Empty derivations and more than 64 engine variants are excluded. These are conservative construction filters, not declarations that the excluded rules are invalid.

The original census contained 552,303 tuples. The prospective Cinvat/mit passive exclusion removes **1,908 tuples across 45 families**. Hidden dictionary prefixes remove **702 more tuples in three test families**: 02.0012, 02.0041 and 10.0368. Entry 02.0042 has the fourth hidden prefix but lies outside this test pool. All **120 pilot entries are clean** before their explicit recipe is applied. No dictionary entry has preloaded sanadi. The reviewed pool therefore has **549,693 tuples across 997 eligible families**.

| Recipe | Eligible families | Unique tuples |
|---|---:|---:|
{recipe_rows}

Every retained family/recipe/lakara/voice cell contains all nine person-number combinations. The smallest cell is intensive-causative aorist active, with 394 families; the nested triple recipe's passive futures retain 591. This is ample raw supply, but quotas and family caps constrain usable diversity. Each family uses the first dictionary entry in the existing canonical order, so duplicate entries do not inflate the census. Exact citation plus gana defines a family, not etymological independence.

## Release sizes and concentration

Max-flow checks establish quota feasibility; a separate min-cost flow maximizes distinct families by penalizing repeat-family units. The displayed allocations are discarded availability witnesses: no task IDs, selected family list, gold answers or final sampling membership are exported. Joint recipe/lakara/voice quotas are rounded from the pilot slot distribution. Person-number balance is constructively feasible because all surviving cells contain all nine pairs and each family-cell group has at most eight tasks.

| Questions | Class policy | Maximum per family | Maximum distinct families | Largest class |
|---:|---|---:|---:|---:|
{capacity_rows}

Keeping the exact pilot class proportions requires a cap of five at 1,000 questions and eight at 1,601; lower caps fail. The supply-adjusted proposal limits each family to two questions while keeping every class. At 1,000 it uses 758 families once and 121 twice; at 1,601 it uses 309 once and 646 twice. This modestly increases Bhvadi concentration to about 51.7%, an explicit diversity-versus-repetition tradeoff.

| Class | Eligible families | Proposed 1,000 tasks | Proposed 1,601 tasks |
|---|---:|---:|---:|
{class_rows}

At 1,000, the six recipe counts are 80, 80, 170, 170, 250 and 250; each lakara has 100 tasks. At 1,601 they are 130, 130, 270, 270, 401 and 400; nine lakaras have 160 tasks and Lan has 161. Karmani remains approximately one quarter. Each person-number cell has 111–112 or 177–178 tasks respectively. All ten classes remain represented; aorist and benedictive each stay near 10%. These remain feasibility proposals, not frozen weights.

## Source audit and the passive oracle issue

Five additional direct source controls supplement the original eight checks. Ordinary causal Sam has documented passive `SAmitA` and `SAmizyate` alongside short and retained-causal-suffix alternatives; VP 0.4.0 omits these long-vowel branches. The relevant rule explicitly extends the cin behavior to these passive contexts. [Kashika and Nyasa on 6.4.62](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.62.htm)

The intensive-causal periphrastic future `SaMSAmitA` is also explicitly documented and missing from VP. Literal-cin aorist controls retain both lengths correctly. Some commentaries differ over nested lengthening, so the direct examples establish a documented alternative rather than a universally agreed single derivation. Source inspection suggests the implementation checks literal ciR/Ramul for 6.4.93 while omitting the Cinvat-tagged condition. [Balamanorama, Kashika and Tattvabodhini on 6.4.93](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.93.htm)

The conservative prospective filter excludes Karmani Lut/Lrt contexts whose combined trace contains **both 6.4.62 and 6.4.92**. It does not exclude either rule alone. One pilot task, 01.1136 nam with `[yaN, Ric]` in passive Lut third singular, meets this condition. Its model answer lengthens while retaining causal aya; the documented long branch deletes nic, so there is **no demonstrated model-score correction**. Original questions, gold, responses and scores remain unchanged. The 4D worker independently checked that none of their twelve passive pilot tasks meets the combined-rule diagnostic.

Nested intensive-to-causative and further desiderative formation have direct printed examples, including `vevidayAmi` and `vevidayizAmi`; that licenses the recipes but does not certify every uncommon complete form. The jF/JF short-vowel ordering reviews and lih vowel-preservation review remain explicitly marked as composition inference or analogy. Nested passive licensing is also composition-based beyond the direct controls. [Whitney §1025 and related sections](https://en.wikisource.org/wiki/Sanskrit_Grammar_(Whitney)/Chapter_XIV#1025)

## Development result and next experiment

| Recipe | Correct / completed | Accuracy | Refusals |
|---|---:|---:|---:|
{score_rows}

The completed-answer estimate is 85.22%, with an independent Wilson 95% interval of 77.60–90.56% and SE of 3.31 percentage points. The 98/120 all-request rate is 81.67%; it includes five refusals and must not be reported as grammatical accuracy. There were no truncations or infrastructure failures. The coordinator-recorded upper actual cost is $1.636686. All 17 completed disagreements were regenerated and categorized; no answer was relabeled.

The two approximately 79% recipe estimates each have fewer than 30 completed answers. Increasing their weight is a development hypothesis, not proof of a target-achieving mixture. The triple recipe is easier than those two in this small sample, so operation count alone is not a difficulty scale. Keep broad tense/class coverage and use fresh tasks for changed weights. The next-step request is **on hold pending oracle-scope resolution**; it proposes a paired fresh development panel only after the coordinator adopts exclusions or repairs the gold and freezes a new task file. The existing Cartesian adapter suffices.

## Precision limits

At 80%, 1,000 independent Bernoulli tasks have SE 1.2649 percentage points. At 1,601 the independent SE is 0.9997 points, barely below one. Repeated-family dependence changes the variance. For the discarded designs, the illustrative exchangeable model uses `DE = 1 + (sum(m_f²)/N - 1) × rho`; rho is an assumed within-family correlation, not an observed statistic.

| Questions | Class policy | SE if rho = 0 | SE if rho = .05 | SE if rho = .10 | SE if rho = .20 |
|---:|---|---:|---:|---:|---:|
{se_rows}

All SE values in the table are percentage points. Even slight positive correlation defeats the nominal 1,601-task guarantee. The 997-family limit also prevents interpreting every tuple as an independent root. Broader linguistic dependence and model run variation are not captured by this simple family model. At the lower target endpoint of 79%, even independent 1,601-task SE is about 1.018 points; strict sub-one-point SE needs at least 1,660 independent questions there. Predeclare sample size and any extension rule before final answers, and report both a task-level estimate and a root-family cluster estimate. No final sample can be certified below one point from supply counts alone.

## Artifacts and remaining work

`release-feasibility-01.json` contains reviewed counts, capacity checks, development evidence and design-specific precision. `release-feasibility-01.reviewed-supply.json` contains family-level availability masks without answers; the original census and pre-audit analysis remain for provenance. `release-feasibility-01.passive-oracle-review.json`, `pilot-01.hidden-modifier-audit.json`, `pilot-01.result-review.json` and `pilot-01.post-modifier-runner-audit.json` record the audits. `release-feasibility-01.next-step-request.json` is a held advisory request, not an executable paid submission.

The bounded feasibility work is complete. Final grammar adjudication, fresh calibration against both references, frozen release membership, separate RL examples and empirical final precision remain outstanding. `benchmark_ready` stays false.
'''
    (OUT/'release-feasibility-01.md').write_text(report)
    print(json.dumps({'accepted_tuples':analysis['accepted_tuples'],'eligible_families':analysis['eligible_master_test_families'],
        'proposal':analysis['recommended_capacity_tradeoff']['results'],'request_status':request['status']},indent=2))


if __name__=='__main__':main()
