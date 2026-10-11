"""Fixed two-chunk pilot07 analysis. No submissions, no partial score analysis.

Prepare an immutable analysis declaration before results. Analyze only after both
declared 1200-question result files exist and match all 2400 frozen tasks exactly.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from collections import Counter, defaultdict
from misc.vp_5d_prepare_04 import ROOT, OUT, atomic_json, now, sha
from misc.vp_5d_novelty_04 import normalized
from misc.vp_cartesian_analyze import completed, metric
from misc.vp_cartesian_final_analyze import panel_statistics
from misc.vp_cartesian_task import entry_scope_issue, oracle_issue
from misc.vp_campaign_candidates import load_entries

DEPENDENCIES = ['misc/vp_5d_analyze_07.py','misc/vp_cartesian_final_analyze.py',
                'misc/vp_cartesian_analyze.py','misc/vp_goal_stats.py']

def read(path):
    return json.loads(Path(path).read_text())

def verify_panel(directory):
    manifest=read(directory/'manifest.json');plan=read(directory/'plan.json')
    for filename,record in manifest['files'].items():
        if sha(directory/filename)!=record['sha256']:
            raise ValueError('Frozen panel file changed: '+filename)
    tasks=read(directory/'tasks.json');transport=read(directory/'transport-plan.json')
    if len(tasks)!=2400 or plan['fixed_development_n']!=2400:
        raise ValueError('Expected fixed N=2400')
    if len(transport['chunks'])!=2:
        raise ValueError('Expected exactly two transport chunks')
    chunks=[]
    for chunk in transport['chunks']:
        path=Path(chunk['tasks_path'])
        if sha(path)!=chunk['sha256']:
            raise ValueError('Frozen chunk changed')
        rows=read(path)
        if len(rows)!=1200 or [t['id'] for t in rows]!=chunk['ids']:
            raise ValueError('Frozen chunk membership/order changed')
        chunks.append(rows)
    if chunks[0]+chunks[1]!=tasks or len({t['id'] for t in tasks})!=2400:
        raise ValueError('Chunks are not an exact disjoint ordered partition')
    if any(t['campaign']['split']!='development' for t in tasks):
        raise ValueError('This analyzer cannot read held-out tasks')
    return tasks,chunks,plan

def prepare(directory):
    directory=directory.resolve()
    if (directory/'analysis-predeclaration.json').exists():
        raise ValueError('Preserve the existing analysis declaration')
    tasks,chunks,plan=verify_panel(directory)
    old_exposure=read(directory/'exposure-and-novelty-audit.json')
    prior=set()
    for record in old_exposure['historical_input_snapshot']['task_files']:
        path=Path(record['path'])
        if sha(path)!=record['sha256']:
            raise ValueError('Historical task input snapshot changed')
        for task in read(path):
            key=normalized(task)[0]
            if key is not None:
                prior.add((key[0]+'|'+key[1],tuple(key[2])))
    groups={t['id']:dict(family=t['campaign']['root_family'],
                        recipe=t['derivation']['recipe_id'],
                        previously_exposed_same_recipe=(t['campaign']['root_family'],tuple(t['derivation']['sanadi'])) in prior)
            for t in tasks}
    expected=old_exposure['question_count_with_prior_same_recipe_family_exposure']
    if sum(x['previously_exposed_same_recipe'] for x in groups.values())!=expected:
        raise ValueError('Exposure classification differs from frozen input audit')
    atomic_json(directory/'analysis-exposure-groups.json',groups)
    declaration=dict(created_at=now(),panel_directory=str(directory),fixed_n=2400,
      result_chunks_required=2,result_n_per_chunk=1200,
      frozen_files={name:sha(directory/name) for name in ['tasks.json','plan.json','manifest.json','transport-plan.json','analysis-exposure-groups.json']},
      analysis_dependencies={name:sha(ROOT/name) for name in DEPENDENCIES},
      bootstrap_repetitions=20000,bootstrap_seed=202610071107,
      completed_predicate='status==completed AND parsed answer non-null AND not truncated, from misc.vp_cartesian_analyze.completed',
      primary_denominator='Every one of the frozen 2400 tasks, without replacement or outcome-based filtering.',
      current_scope_supplement='Apply current shared entry/oracle predicates uniformly to all outcomes, report exact excluded IDs and reason, retain raw full-panel statistics. Scope changes need a validity review and cannot silently qualify the original design.',
      advancement_rule=plan['fixed_decision_rule'],
      numerical_screen='All-request and usable point estimates and both missing-response bounds must each lie in [0.79,0.81]. No rounding before comparison. Require both full chunks and no infrastructure-unscored result. A numerical pass remains provisional pending independent validity review.',
      precision='Report iid and family sandwich SE plus whole-family and class-stratified whole-family bootstrap sensitivity. Development advancement has no invented precision pass; final both-model sub1pp gate is separate.',
      subgroup_metrics=['recipe','lakara','voice','class','recipe×lakara×voice','same-recipe family prior exposure'],
      missing='Refusals, truncations and missing parsed answers remain unknown for bounds. Preserve recorded all-request correctness separately, including any correctly parsed truncated row.',
      sequential_rule='Do not read or summarize one chunk alone. Both 1200 transport chunks must match before any aggregate estimate or target screen. No score-based stopping, replacement, or reweighting.',
      family_exposure='All selected development families were previously exposed. A same-recipe-new group is not a new lexical-family group. Legacy6687 analysis inspected all dictionary families, including later master test families; the new campaign split excludes reserved-family legacy records from discovery fitting.',
      benchmark_ready=False,final_n_approved=False)
    atomic_json(directory/'analysis-predeclaration.json',declaration)
    print(json.dumps(dict(declaration=str(directory/'analysis-predeclaration.json'),sha256=sha(directory/'analysis-predeclaration.json'),analyzer_sha256=sha(Path(__file__))),indent=2))

def verify_results(chunks,results):
    if len(results)!=2:
        raise ValueError('Both result chunks are required before analysis')
    all_rows=[]
    for expected,rows in zip(chunks,results):
        mapping={t['id']:t for t in expected}
        if len(rows)!=1200 or len({r['task']['id'] for r in rows})!=1200:
            raise ValueError('Incomplete or duplicate result chunk')
        if {r['task']['id'] for r in rows}!=set(mapping):
            raise ValueError('Result chunk does not match the frozen partition')
        for row in rows:
            if row['task']!=mapping[row['task']['id']]:
                raise ValueError('Result task metadata differs from frozen panel')
        byid={r['task']['id']:r for r in rows}
        all_rows.extend(byid[t['id']] for t in expected)
    return all_rows

def screen(stats):
    values=[stats['all_request']['accuracy'],stats['completed_answer']['accuracy'],*stats['missing_answer_accuracy_bounds']]
    return bool(stats['all_results_present'] and not stats['unscored_results'] and
                all(x is not None and .79<=x<=.81 for x in values))

def describe(tasks,rows,groups,decl):
    if not tasks:
        return dict(n=0,numerical_screen=False,reason='No retained tasks')
    stats=panel_statistics(tasks,rows,repetitions=decl['bootstrap_repetitions'],seed=decl['bootstrap_seed'])
    strata=defaultdict(list);family=defaultdict(list)
    for row in rows:
        t=row['task'];m=t['morphology'];r=t['derivation']['recipe_id']
        vals=dict(recipe=r,lakara=m['lakara'],voice=m['prayoga'],gana=t['dhatu']['gana'],
                  recipe_lakara_voice='|'.join([r,m['lakara'],m['prayoga']]),
                  same_recipe_exposure='previously_exposed' if groups[t['id']]['previously_exposed_same_recipe'] else 'new_recipe_for_exposed_family')
        for field,value in vals.items(): strata[field+'::'+value].append(row)
        family[t['campaign']['root_family']].append(row)
    pairs=defaultdict(Counter)
    for rs in family.values():
        for i,left in enumerate(rs):
            for right in rs[i+1:]:
                a,b=left['task']['morphology']['lakara'],right['task']['morphology']['lakara']
                key='both_Lun' if a==b=='Lun' else 'mixed_Lun_other' if 'Lun' in [a,b] else 'both_non_Lun'
                pairs[key]['all_pairs']+=1
                usable=completed(left) and completed(right)
                pairs[key]['jointly_usable_pairs']+=int(usable)
                pairs[key]['all/'+str(int(left['is_correct'] is True))+str(int(right['is_correct'] is True))]+=1
                if usable:pairs[key]['usable/'+str(int(left['is_correct'] is True))+str(int(right['is_correct'] is True))]+=1
    return dict(statistics=stats,numerical_screen=screen(stats),
      strata={k:metric(v) for k,v in sorted(strata.items())},
      family_load_histogram=dict(Counter(len(v) for v in family.values())),
      family_aorist_load_histogram=dict(Counter(sum(r['task']['morphology']['lakara']=='Lun' for r in v) for v in family.values())),
      pair_diagnostics={k:dict(v) for k,v in pairs.items()},
      caveat='Pair tables overlap within families and are descriptive; they are not additional independent samples.')

def analyze(directory,paths):
    directory=directory.resolve()
    # Check both paths before opening either result file; no first-chunk analysis.
    if len(paths)!=2 or not all(p.is_file() for p in paths):
        raise ValueError('Both complete result files must be present; no interim scores')
    if any(not p.parent.name.startswith('opus-five-d-pilot-07') for p in paths):
        raise ValueError('Only named Opus pilot07 development jobs are allowed')
    tasks,chunks,plan=verify_panel(directory)
    declaration=read(directory/'analysis-predeclaration.json')
    for filename,digest in declaration['frozen_files'].items():
        if sha(directory/filename)!=digest:raise ValueError('Analysis input changed: '+filename)
    for filename,digest in declaration['analysis_dependencies'].items():
        if sha(ROOT/filename)!=digest:raise ValueError('Frozen analyzer dependency changed: '+filename)
    rows=verify_results(chunks,[read(p) for p in paths])
    groups=read(directory/'analysis-exposure-groups.json')
    entries={e.code:e for e in load_entries()};kept=[];excluded=[]
    for row in rows:
        task=row['task'];issue=entry_scope_issue(entries[task['dhatu']['code']]) or oracle_issue(task)
        if issue:excluded.append(dict(id=task['id'],reason=issue,status=row['status'],recorded_correct=row['is_correct']))
        else:kept.append(row)
    raw=describe(tasks,rows,groups,declaration)
    supplemental=describe([r['task'] for r in kept],kept,groups,declaration)
    out=dict(created_at=now(),panel=str(directory),fixed_n=2400,
      analysis_predeclaration_sha256=sha(directory/'analysis-predeclaration.json'),
      result_sources=[dict(path=str(p),sha256=sha(p)) for p in paths],
      current_scope_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),
      raw=raw,current_scope_supplement=supplemental,scope_exclusions=excluded,
      original_raw_records_changed=False,all_chunks_present=True,
      advancement=dict(raw_numerical_screen=raw['numerical_screen'],
                       current_scope_numerical_screen=supplemental['numerical_screen'],
                       validity_review_required=True,authorized=False,
                       explanation='No automatic advancement or benchmark qualification; audit disagreements and missing responses, then coordinator resolves retained-scope validity.'),
      benchmark_ready=False,limitations=[
        'Fixed development mixture was chosen adaptively from earlier panels; intervals omit selection and oracle uncertainty.',
        'Fresh exact tuples reuse previously exposed development families. Exposure subgroup differences are observational and can be composition-confounded.',
        'Legacy6687 analysis inspected all dictionary families. New campaign reserved-family separation is not a never-seen-lexical-root claim.',
        'Opus-only family dependence cannot identify Astra repeated-aorist covariance or final output-cap effects.',
        'Repeated forms, imbalance and few families in some classes limit resampling interpretations; no estimator choice changes the final precision gate.'])
    target=directory/'aggregate-analysis.json'
    if target.exists():raise ValueError('Preserve prior aggregate; use an explicit versioned analysis output for revisions')
    atomic_json(target,out)
    print(json.dumps(dict(output=str(target),raw=raw['statistics'],current_scope=supplemental.get('statistics'),advancement=out['advancement']),indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','analyze']);parser.add_argument('directory',type=Path)
    parser.add_argument('results',type=Path,nargs='*');args=parser.parse_args()
    if args.command=='prepare':prepare(args.directory)
    else:analyze(args.directory,args.results)
