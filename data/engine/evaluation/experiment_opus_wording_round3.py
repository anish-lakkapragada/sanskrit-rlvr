"""100 additional calls: 40 focused comparisons, 40 fresh checks, 20 repeated checks.

Only the three run stages call the API. Preserve every request, including repeats.
"""

import argparse
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import random
import re
import string
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation import experiment_opus_wording as common

opus, base = common.opus, common.base
FOLDER = ROOT / "data/benchmark/experiments/opus55-cyber-wording-round3"
CANDIDATES = common.FOLDER / "candidate-templates"
FAMILIES = ("tinanta", "krdanta", "taddhitanta", "subanta")
VARIANTS = ("current", "positive_format", "semantic_scope", "quoted_fields", "data_first")
LAYOUTS = ("current", "sentences", "table", "compact_fields", "sentence_question")
STAGES = {"discovery":40,"validation":40,"stress":20}
HARD = "taddhitanta:loqana:basic:Napumsaka:TAl"
TINANTA = "06.0035:Lan:Kartari:Uttama:Bahu"
ANSWER = ("Your complete response should consist of a single <answer>...</answer> block "
          "containing one valid final Sanskrit form in Devanagari. If multiple forms are valid, choose one.")


def transform(prompt, family, variant):
    if variant == "current":
        return prompt
    instructions, fields = prompt.split("=== Your task ===",1)
    if variant in LAYOUTS:
        if family != 'taddhitanta':
            return prompt
        get=lambda prefix:next(line[len(prefix):] for line in fields.splitlines() if line.startswith(prefix))
        stem=get('pratipadika (nominal base): ')
        interpretation=get('base interpretation: ')
        affix=re.fullmatch(r'(.+) \(SLP1: (.+)\)',get('taddhita (technical affix): '))
        suffix,identifier=affix.groups()
        answer='Write ONLY the final form'+instructions.split('Write ONLY the final form',1)[1].rstrip()
        result_rule='Give the derived nominal stem or complete indeclinable without adding case or number endings. Any meaning licensed for this affix is acceptable.'
        if variant=='sentences':
            body=f'Complete this Sanskrit word-formation exercise.\n\nThe given nominal stem is {stem}. Its grammatical interpretation is: {interpretation}.\nThe requested taddhita affix is {suffix}, identified as {identifier} in SLP1.\n{result_rule}'
        elif variant=='sentence_question':
            body=f'What is the Sanskrit taddhita derivative of {stem} formed with {suffix} (SLP1: {identifier})?\n\nTreat the supplied stem as follows: {interpretation}.\n{result_rule}'
        elif variant=='table':
            body=f'Form the Sanskrit taddhita derivative described in this table.\n\n| Grammatical input | Value |\n| --- | --- |\n| Nominal stem | {stem} |\n| Interpretation of the stem | {interpretation} |\n| Taddhita affix | {suffix} |\n| Technical identifier in SLP1 | {identifier} |\n\n{result_rule}'
        else:
            body='Form a Sanskrit taddhitanta using the supplied nominal base and taddhita. Respect the stated interpretation of the base. '+result_rule
            return body+'\n\n'+answer+'\n\n=== Your task ==='+fields
        return body+'\n\n'+answer+'\n'
    if variant == "positive_format":
        intro = instructions.split("Write ONLY the final form",1)[0].rstrip()
        return intro + "\n\n" + ANSWER + "\n\n=== Your task ===" + fields
    if variant == "semantic_scope":
        return prompt.replace("artha (meaning): unrestricted",
            "artha (meaning): no particular semantic relation is specified; use any relation licensed by Sanskrit grammar").replace(
            "artha (traditional meaning):", "artha (dictionary gloss identifying the Sanskrit verb):")
    if variant == "quoted_fields":
        return instructions + "=== Your task ===\n\n```text\n" + fields.strip() + "\n```\n"
    if variant == "data_first":
        return "=== Your task ===" + fields.rstrip() + "\n\n" + instructions.strip() + "\n"
    raise ValueError(variant)


def metrics(rows):
    return common.metrics(rows)


def summary(records):
    rows = list(records.values())
    return {"total":metrics(rows),"stages":{
        stage:{"arms":{v:metrics([r for r in rows if r['phase']==stage and r['variant']==v])
                       for v in sorted({r['variant'] for r in rows if r['phase']==stage})},
               "families":{f:metrics([r for r in rows if r['phase']==stage and r['family']==f]) for f in FAMILIES}}
        for stage in STAGES}}


def make_plan(cases, stage, selection=None):
    result=[]
    for c in cases:
        if c['phase']!=stage:
            continue
        variants=VARIANTS if stage=='discovery' else LAYOUTS if stage=='validation' else (selection[c['family']],)
        for v in variants:
            result.append({"request_key":f"{stage}:{c['case_id']}:{v}","case_id":c['case_id'],
                           "family":c['family'],"task_id":c['task']['id'],"phase":stage,"variant":v,
                           "prompt":transform(c['current_prompt'],c['family'],v)})
    random.Random({'discovery':69,'validation':70,'stress':71}[stage]).shuffle(result)
    assert len(result)==STAGES[stage]
    return result


def choose(records, cases, previous=None):
    """Use discovery evidence; after validation, reconsider only families with failures."""
    rows=list(records.values())
    case_map={c['case_id']:c for c in cases}
    chosen={}
    for family in FAMILIES:
        if previous and not any(r['phase']=='validation' and r['family']==family and r['status']=='refused' for r in rows):
            chosen[family]=previous[family]
            continue
        choices=[]
        for v in VARIANTS:
            group=[r for r in rows if r['family']==family and r['variant']==v]
            hard=[r for r in group if case_map[r['case_id']]['task']['id']==HARD]
            stat=metrics(group)
            # Compare rates because validation adds observations for one candidate.
            hard_rate=sum(r['status']=='refused' for r in hard)/len(hard) if hard else 0
            refusal_rate=stat['refusals']/len(group)
            accuracy=stat['strict_correct']/len(group)
            order=(VARIANTS[1:]+VARIANTS[:1]) if family=='taddhitanta' else VARIANTS
            choices.append(((hard_rate,refusal_rate,-accuracy,order.index(v)),v))
        chosen[family]=min(choices)[1]
    return chosen


def choose_layouts(records,cases):
    rows=[r for r in records.values() if r['phase']=='validation']
    if len(rows)!=40 or any(r['status'] not in ('completed','refused') for r in rows):
        raise RuntimeError('Need all 40 layout outcomes')
    chosen=dict.fromkeys(FAMILIES,'current')
    # Other-family layout arms send identical current prompts; do not select on their random variation.
    choices=[]
    for v in LAYOUTS:
        group=[r for r in rows if r['family']=='taddhitanta' and r['variant']==v]
        hard=[r for r in group if r['task_id']==HARD]
        stats=metrics(group)
        preference=LAYOUTS[1:]+LAYOUTS[:1]
        choices.append(((sum(r['status']=='refused' for r in hard),stats['refusals'],-stats['strict_correct'],preference.index(v)),v))
    chosen['taddhitanta']=min(choices)[1]
    return chosen


def amend_layout_stage(folder):
    with (folder/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        m=json.loads((folder/'manifest.json').read_text());old=json.loads((folder/'cases.json').read_text())
        if m['status']!='discovery_complete' or m['submitted_requests']!=40 or m.get('protocol_amendment'):
            raise RuntimeError('Amendment requires 40 settled requests and no previous amendment')
        history=folder/'protocol-history';history.mkdir(exist_ok=True)
        for source,name in ((ROOT/m['script']['path'],'runner-before-layout-tests.py'),(folder/'manifest.json','manifest-before-layout-tests.json'),(folder/'cases.json','cases-before-layout-tests.json')):
            target=history/name
            if not target.exists():target.write_bytes(source.read_bytes())
        old_script=opus.descriptor(history/'runner-before-layout-tests.py')
        if old_script['sha256']!=m['script']['sha256'] or common.sha(old)!=m['cases_sha256']:raise RuntimeError('Snapshot mismatch')
        if json.loads((history/'manifest-before-layout-tests.json').read_text())!=m or json.loads((history/'cases-before-layout-tests.json').read_text())!=old:raise RuntimeError('Input history mismatch')
        _,starts,records=common.recover(folder,m,old)
        if len(starts)!=40 or set(starts)!=records.keys():raise RuntimeError('Unresolved calls')
        cases=[deepcopy(c) for c in old if c['phase']=='discovery']
        for i,c in enumerate(list(cases)):
            copy=deepcopy(c);copy.update(case_id=f'layout_{i+1:02}',phase='validation',reason='Second-stage layout comparison; same cases as discovery')
            cases.append(copy)
        final=[]
        for f in FAMILIES:
            fresh=[c for c in old if c['phase']=='validation' and c['family']==f]
            if f=='taddhitanta':
                hard=next(c for c in old if c['task']['id']==HARD)
                selected=[hard,hard,hard,*fresh[:2]]
            elif f=='tinanta':
                hard=next(c for c in old if c['task']['id']==TINANTA)
                selected=[hard,*fresh[:4]]
            else:selected=fresh[:5]
            for c in selected:
                copy=deepcopy(c);copy.update(case_id=f'final_{len(final)+1:02}',phase='stress',reason='Fresh confirmation task' if c['phase']=='validation' else 'Known challenge repetition')
                final.append(copy)
        cases.extend(final)
        assert len(cases)==36 and len(final)==20
        m['protocol_amendment']={'at':base.now(),'after_requests':40,
            'reason':'Every first-stage variant refused the persistent case at least once in three calls. Use the next 40 for four new layouts plus a current-template control; preserve 20 calls for final confirmation.',
            'layouts':list(LAYOUTS),'selection':'For taddhitanta: fewest persistent-case refusals, fewest total refusals, most strict correct. Prefer changed layouts on ties. Other families keep current templates because their layout-stage requests are identical controls.',
            'final_confirmation':'16 fresh tasks plus three persistent taddhitanta repeats and one persistent tinanta. Five calls per category.',
            'prior_script':old_script,'prior_manifest':opus.descriptor(history/'manifest-before-layout-tests.json'),'prior_cases':opus.descriptor(history/'cases-before-layout-tests.json')}
        m['script']=opus.descriptor(Path(__file__));m['cases_sha256']=common.sha(cases)
        m['design']='40 initial wording comparisons, 40 additional layout comparisons on the same cases, then 20 prospectively selected confirmation calls (16 fresh, four challenge calls). Stage named validation is now further tuning, not an independent holdout.'
        common.write_json(folder/'cases.json',cases);common.write_json(folder/'manifest.json',m)
        return m['protocol_amendment']


def prepare(folder):
    if folder.exists() and any(folder.iterdir()):
        raise RuntimeError('Existing experiment; budget cannot be reset')
    source,tasks,prompts,_=opus.load_inputs()
    templates={f:(CANDIDATES/f'vp_{f}.txt').read_text() for f in FAMILIES}
    production={t['family']:t['prompt_template']['text'] for t in source['tasks']}
    for f in FAMILIES:
        if templates[f].split('=== Your task ===',1)[1]!=production[f].split('=== Your task ===',1)[1]:
            raise RuntimeError('Baseline fields differ from production; inspect hydration')
    prior=set()
    for directory in (common.FOLDER, ROOT/'data/benchmark/experiments/opus55-cyber-wording-round2'):
        for c in json.loads((directory/'cases.json').read_text()):
            prior.add((c['family'],c['task']['id']))
    results={f:{r['task_id']:r for r in json.loads((opus.RUN/f'{f}.json').read_text())} for f in FAMILIES}
    cases=[]
    def add(family,task_id,phase,reason):
        prompt=templates[family].split('=== Your task ===',1)[0]+'=== Your task ==='+prompts[family,task_id].split('=== Your task ===',1)[1]
        cases.append({'case_id':f'case_{len(cases)+1:02}','family':family,'phase':phase,'reason':reason,
                      'task':tasks[family][task_id],'original_prompt':prompts[family,task_id],
                      'current_prompt':prompt,'original_benchmark_result':results[family][task_id]})
    rng=random.Random(69)
    krd=next(k for k,r in sorted(results['krdanta'].items()) if r['status']=='refused' and r.get('error',{}).get('stop_details',{}).get('category')=='cyber')
    sub=rng.choice(sorted(k for k,r in results['subanta'].items() if r['status']=='completed'))
    for _ in range(3):add('taddhitanta',HARD,'discovery','Repeated persistent failure')
    for f,t in [('taddhitanta','taddhitanta:selaga:basic:Pum:Sas'),('taddhitanta','taddhitanta:AntrikI:nyap:Stri:kan'),('tinanta',TINANTA),('krdanta',krd),('subanta',sub)]:
        add(f,t,'discovery','Cross-task comparison')
    used=prior|{(c['family'],c['task']['id']) for c in cases}
    sampling={}
    for f in FAMILIES:
        available=[k for k,r in results[f].items() if (f,k) not in used and r['status'] in ('completed','refused')]
        flagged=sorted(k for k in available if results[f][k]['status']=='refused' and results[f][k].get('error',{}).get('stop_details',{}).get('category')=='cyber')
        normal=sorted(k for k in available if results[f][k]['status']=='completed')
        n=min(5,len(flagged))
        selected=rng.sample(flagged,n)+rng.sample(normal,10-n)
        sampling[f]={'fresh_previously_refused':n,'fresh_previously_completed':10-n}
        for k in selected:add(f,k,'validation','Fresh task not used in previous wording rounds')
    stress={'tinanta':TINANTA,'krdanta':krd,'taddhitanta':HARD,'subanta':sub}
    for f,k in stress.items():
        for _ in range(5):add(f,k,'stress','Five identical-prompt repetitions to check consistency')
    assert len(cases)==68
    plan=make_plan(cases,'discovery')
    folder.mkdir(parents=True)
    (folder/'journals').mkdir()
    (folder/'candidate-templates-before').mkdir()
    for f,t in templates.items():base.atomic_write(folder/'candidate-templates-before'/f'vp_{f}.txt',t)
    m={'experiment':'opus55-cyber-wording-round3','created_at':base.now(),'status':'prepared',
       'request_budget':100,'submitted_requests':0,'seed':69,'request_defaults':deepcopy(opus.REQUEST_DEFAULTS),
       'pricing':source['pricing'],'source_tasks':source['tasks'],'baseline_templates':templates,
       'cases_sha256':common.sha(cases),'script':opus.descriptor(Path(__file__)),
       'dependencies':[opus.descriptor(Path(common.__file__)),opus.descriptor(Path(opus.__file__)),opus.descriptor(Path(base.__file__)),source['scoring']['implementation']],
       'stages':{s:{'requests':n,'status':'prepared' if s=='discovery' else 'awaiting_selection'} for s,n in STAGES.items()},
       'validation_sampling':sampling,
       'variants':{'current':'Current candidate control.','positive_format':'Express the same answer contract as one positive instruction.',
                   'semantic_scope':'Clarify unspecified semantic relation and dictionary-gloss labels; keep lexical values.',
                   'quoted_fields':'Put unchanged grammatical data in a readable text block.',
                   'data_first':'Put the same task fields before the instructions.'},
       'selection_rule':'Per family: lowest hard-case refusal rate, lowest overall refusal rate, highest strict accuracy. Prefer current on ties except taddhitanta, where prefer a changed variant because current has known prior failures. After validation, reconsider only families with refusals using all recorded observations. Freeze the final selection before stress checks.',
       'design':'Discovery: 5 variants on 8 requests each (3 repeats of the persistent taddhitanta plus 5 cross-task checks). Validation: 10 fresh tasks per family. Stress: 5 identical-prompt calls per family on the persistent taddhitanta, persistent tinanta, and one krdanta/subanta control.',
       'preservation':'100 additional requests maximum; no automatic retries or fallbacks. Preserve all outcomes, including repeated identical prompts. Only candidate templates may change. All Sanskrit inputs, lexical meanings, grammatical coordinates and the one-answer contract remain explicit. A finite zero count is not a guarantee.'}
    m['stages']['discovery']['plan_sha256']=common.sha(plan)
    common.write_json(folder/'cases.json',cases)
    common.write_json(folder/'discovery-plan.json',plan)
    common.write_json(folder/'manifest.json',m)
    common.write_json(folder/'results.json',[])
    return {'planned':STAGES,'validation_sampling':sampling}


def load(folder):
    m=json.loads((folder/'manifest.json').read_text());cases=json.loads((folder/'cases.json').read_text())
    if common.sha(cases)!=m['cases_sha256'] or m['request_defaults']!=opus.REQUEST_DEFAULTS:raise RuntimeError('Pinned inputs changed')
    for d in [m['script'],*m['dependencies']]:base.verify_descriptor(d)
    journal,starts,records=common.recover(folder,m,cases)
    if set(starts)!=records.keys():raise RuntimeError('Unresolved started requests; never automatically resend')
    return m,cases,journal,starts,records


def run_stage(folder,stage):
    with (folder/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        m,cases,journal,starts,records=load(folder)
        config=m['stages'][stage]
        if stage=='validation' and m['stages']['discovery']['status']!='completed':raise RuntimeError('Discovery incomplete')
        if stage=='stress' and 'selection' not in config:
            previous='discovery' if stage=='validation' else 'validation'
            if m['stages'][previous]['status']!='completed':raise RuntimeError('Previous stage incomplete')
            if any(r['status'] not in ('completed','refused') for r in records.values()):raise RuntimeError('Inspect API failures before selection')
            config['selection']=choose_layouts(records,cases)
            config['selected_at']=base.now()
            common.write_json(folder/'manifest.json',m)
        plan=make_plan(cases,stage,config.get('selection'))
        planfile=folder/f'{stage}-plan.json'
        if planfile.exists():
            if json.loads(planfile.read_text())!=plan or common.sha(plan)!=config['plan_sha256']:raise RuntimeError('Plan changed')
        else:
            common.write_json(planfile,plan);config['plan_sha256']=common.sha(plan)
        pending=[p for p in plan if p['request_key'] not in starts]
        if len(starts)+len(pending)>100:raise RuntimeError('Budget exceeded')
        for p in plan:
            if p['request_key'] in starts and starts[p['request_key']]['request']!=opus.request_body(p['prompt']):raise RuntimeError('Started prompt changed')
        key=os.environ.get('ANTHROPIC_API_KEY') or opus.dotenv_values(ROOT/'.env').get('ANTHROPIC_API_KEY')
        if pending and not key:raise RuntimeError('Missing Anthropic key')
        cmap={c['case_id']:c for c in cases};cursor=0;futures={};stop=None
        m['status']='running';config['status']='running'
        def checkpoint():
            m.update(submitted_requests=len(starts),updated_at=base.now(),stopped_reason=stop)
            common.write_json(folder/'results.json',sorted(records.values(),key=lambda r:r['request_key']))
            common.write_json(folder/'summary.json',summary(records));common.write_json(folder/'manifest.json',m)
        checkpoint()
        with opus.httpx.Client(timeout=opus.httpx.Timeout(1800,connect=30),follow_redirects=False,transport=opus.httpx.HTTPTransport(retries=0)) as client, ThreadPoolExecutor(max_workers=8) as pool:
            while cursor<len(pending) or futures:
                while not stop and cursor<len(pending) and len(futures)<8:
                    if len(starts)>=100:raise RuntimeError('Request budget exhausted')
                    p=pending[cursor];cursor+=1;body=opus.request_body(p['prompt']);client_id=str(uuid.uuid4())
                    marker={'event':'started','task_id':p['request_key'],'attempt_number':1,'timestamp':base.now(),'client_request_id':client_id,'plan':p,'request':body}
                    journal.append(marker);starts[p['request_key']]=marker
                    futures[pool.submit(opus.execute,client,m,p['request_key'],body,client_id,journal,key)]=p
                if not futures:break
                done,_=wait(futures,timeout=10,return_when=FIRST_COMPLETED)
                for future in done:
                    p=futures.pop(future);row=opus.result_row(future.result(),cmap[p['case_id']]['task'],m)
                    records[p['request_key']]={**{k:p[k] for k in ('request_key','case_id','family','phase','variant')},**row}
                    if row['status'] not in ('completed','refused') or row['cost_usd'] is None:stop=f"Inspect {p['request_key']}: {row['status']}"
                checkpoint()
                print(base.compact({'stage':stage,'submitted':len(starts),'settled':len(records),'in_flight':len(futures),'stop':stop}),flush=True)
        complete=all(p['request_key'] in records for p in plan)
        config['status']='completed' if complete else 'paused'
        m['status']='completed' if stage=='stress' and complete else stage+'_complete' if complete else 'paused'
        checkpoint()
        if m['status']=='completed':journal.archive()
        return summary(records)


def finalize(folder):
    with (folder/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        m,cases,journal,starts,records=load(folder)
        if m['status']!='completed' or len(starts)!=100 or len(records)!=100:raise RuntimeError('Need all 100 outcomes')
        if sorted(records.values(),key=lambda r:r['request_key'])!=json.loads((folder/'results.json').read_text()):raise RuntimeError('Journal replay mismatch')
        if summary(records)!=json.loads((folder/'summary.json').read_text()):raise RuntimeError('Summary mismatch')
        for stage in STAGES:
            plan=make_plan(cases,stage,m['stages'][stage].get('selection'))
            if plan!=json.loads((folder/f'{stage}-plan.json').read_text()) or common.sha(plan)!=m['stages'][stage]['plan_sha256']:raise RuntimeError('Plan mismatch')
            for p in plan:
                if starts[p['request_key']]['request']!=opus.request_body(p['prompt']):raise RuntimeError('Request mismatch')
        for entry in m['source_tasks']:
            for name in ('dataset','sampling_manifest','prompt_template','renderer'):base.verify_descriptor(entry[name])
        extras={'request_key','case_id','family','phase','variant'};validator=opus.Draft202012Validator(opus.schema())
        for r in records.values():validator.validate([{k:v for k,v in r.items() if k not in extras}])
        selection=m['stages']['stress']['selection'];cmap={c['case_id']:c for c in cases};matching=[]
        for k,r in records.items():
            prompt=transform(cmap[r['case_id']]['current_prompt'],r['family'],selection[r['family']])
            if starts[k]['request']==opus.request_body(prompt):matching.append(r)
        output=folder/'candidate-templates-after';output.mkdir(exist_ok=True);updated={}
        for f in FAMILIES:
            original=m['baseline_templates'][f];new=transform(original,f,selection[f]);target=CANDIDATES/f'vp_{f}.txt'
            fields=lambda x:sorted(field for _,field,_,_ in string.Formatter().parse(x) if field)
            if fields(original)!=fields(new):raise RuntimeError('Template placeholder set changed')
            if target.read_text() not in (original,new):raise RuntimeError('Candidate modified externally')
            base.atomic_write(output/target.name,new);base.atomic_write(target,new);updated[f]=opus.descriptor(target)
        verified={'verified_at':base.now(),'verified_requests':100,'final_selection':selection,'updated_templates':updated,
                  'stress':metrics([r for r in records.values() if r['phase']=='stress']),
                  'matching_final_template_all_phases':metrics(matching),
                  'matching_final_template_by_family':{f:metrics([r for r in matching if r['family']==f]) for f in FAMILIES},
                  'layout_stage_matching_final_template':metrics([r for r in matching if r['phase']=='validation']),
                  'fresh_confirmation_matching_final_template':metrics([r for r in matching if r['phase']=='stress' and cmap[r['case_id']]['reason']=='Fresh confirmation task']),
                  'persistent_case_matching_final_template':metrics([r for r in matching if r['task_id']==HARD]),
                  'zero_observed_matching_final_template_refusals':all(r['status']=='completed' for r in matching),
                  'caveat':'Includes selection data and repeated identical prompts. Stress was prospectively frozen; a finite zero count does not establish zero future refusal probability.'}
        common.write_json(folder/'verification.json',verified)
        m['candidate_update']={'at':verified['verified_at'],'files':updated};common.write_json(folder/'manifest.json',m)
        return verified


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare',*STAGES,'amend','finalize'));p.add_argument('--folder',type=Path,default=FOLDER)
    a=p.parse_args();result=prepare(a.folder) if a.action=='prepare' else amend_layout_stage(a.folder) if a.action=='amend' else finalize(a.folder) if a.action=='finalize' else run_stage(a.folder,a.action)
    print(json.dumps(result,ensure_ascii=False,indent=2))
