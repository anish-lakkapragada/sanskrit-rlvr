"""Source-driven family replacement and approved Sanskrit-renderer freeze."""
from __future__ import annotations
import copy
import json
import random
from collections import Counter,defaultdict
from pathlib import Path
from misc.vp_5d_prepare_04 import ROOT,status
from misc.vp_5d_prepare_03 import RECIPES,SOURCE_ROOTS,task_for
from misc.vp_5d_pilot import OUT,VOWELS,entries,signature,atomic_json,now,sha
from misc.vp_5d_novelty_04 import normalized,walk
from misc.vp_cartesian_task import make_task,validate_task,oracle_issue
from misc.vp_cartesian_prompt_v3 import render
from misc.vp_goal_validate import validate
from misc import vp_campaign_candidates as old
from vidyut.prakriya import Vyakarana

SEED=20261007070491
VERSION='cartesian-5d-v3-sanskrit'

def main():
    output=OUT/'pilot-04.tasks.json'
    if output.exists():raise RuntimeError('Preserve frozen final panel')
    provisional=OUT/'pilot-04.provisional.tasks.json';tasks=json.loads(provisional.read_text());original=copy.deepcopy(tasks)
    oldhash=sha(provisional);es=entries();v=Vyakarana();bases={f:sorted({p.text for p in v.derive(e.dhatu)}) for f,e in es.items()}
    historical=defaultdict(list);historyfamilies=set();inputfiles=[];ledgerhashes=[]
    for name in ['creation-campaign-20261006','iterative-goal-20261006']:
        path=ROOT/'benchmarks'/name/'ledger.json';data=json.loads(path.read_text());ledgerhashes.append({'path':str(path),'sha256':sha(path)})
        for label in data['jobs']:
            source=path.parent/'jobs'/label/'tasks.json';inputfiles.append({'path':str(source),'sha256':sha(source)})
            for task in json.loads(source.read_text()):
                for t in walk(task):
                    f=t.get('campaign',{}).get('root_family')
                    if f:historyfamilies.add(f)
                    sig,issue=normalized(t)
                    if not issue:historical[sig].append({'job':label,'id':t.get('id')})
    prior=[t for n in ['01','02','03'] for t in json.loads((OUT/f'pilot-{n}.tasks.json').read_text())]
    pilotfamilies={t['campaign']['root_family'] for t in prior};families={t['campaign']['root_family'] for t in tasks}
    affected={t['campaign']['root_family'] for t in tasks if oracle_issue(t)}
    assert affected=={'du\\za~|Divadi'}
    rng=random.Random(SEED);replacement=[]
    for bad in sorted(affected):
        indices=[i for i,t in enumerate(tasks) if t['campaign']['root_family']==bad]
        assert len(indices)==2 and all('6.4.91' in tasks[i]['campaign']['trace_rule_ids'] for i in indices)
        pool=[f for f,e in es.items() if f not in families and old.name(e.dhatu.gana)=='Divadi' and e.code not in SOURCE_ROOTS]
        rng.shuffle(pool);pool.sort(key=lambda f:f in pilotfamilies)
        for f in pool:
            built=[]
            for i in indices:
                oldt=tasks[i];t,issue=task_for(es[f],oldt['derivation']['recipe_id'],oldt['morphology'],bases)
                if issue or normalized(t)[0] in historical:break
                built.append((i,t))
            if len(built)==2:break
        else:raise RuntimeError('No same-class/same-cell fresh replacement family')
        for i,t in built:
            oldt=tasks[i]
            for key in ['panel','slot','plan_sha256','selection_reason','sampling_cell']:
                t['campaign'][key]=copy.deepcopy(oldt['campaign'][key])
            t['campaign'].update(lexical_bases=bases[f],oracle_policy='oracle-policy-10',audit_status='Source-driven replacement under unchanged grammar weights; shared regeneration and recipe source audit.')
            replacement.append({'old_id':oldt['id'],'old_code':oldt['dhatu']['code'],'new_id':t['id'],'new_code':t['dhatu']['code'],
              'recipe':t['derivation']['recipe_id'],'morphology':t['morphology'],'reason':'Shared trace6.4.91 semantic-scope quarantine; family replaced before model evaluation.'})
            tasks[i]=t
        families.remove(bad);families.add(f)
    revision=OUT/'pilot-04.revision-01.provisional.tasks.json';atomic_json(revision,tasks)
    revision_report={'created_at':now(),'seed':SEED,'policy':'oracle-policy-10','original_provisional_sha256':oldhash,
      'revision_sha256':sha(revision),'replacements':replacement,'original_file_preserved':sha(provisional)==oldhash,
      'same_recipe_tense_voice_person_number_and_gana_per_replacement':True,'family_pair_structure_preserved':True,
      'selection':'Seeded same-class candidates absent from this panel, preferring families absent from earlier named5D pilots. Both assigned grammar cells must pass shared policy and both exact questions must be absent from both campaign ledgers.',
      'results_used_for_replacement':False}
    atomic_json(OUT/'pilot-04.revision-01.audit.json',revision_report)
    prompts=[]
    for t in tasks:
        e=es[t['campaign']['root_family']]
        r=make_task(e,'development',t['morphology'],t['derivation']['recipe_id'],t['derivation']['sanadi'],prompt_version=VERSION)
        assert r['id']==t['id'] and r['gold_slp1']==t['gold_slp1']
        t['prompt_version']=VERSION;t['campaign'].update(prompt_sha256=r['campaign']['prompt_sha256'],oracle_policy='oracle-policy-10')
        validate_task(t,e,'development');prompts.append({'id':t['id'],'prompt':render(t)})
        assert normalized(t)[0] not in historical
    p=json.loads((OUT/'pilot-04.plan.json').read_text());famcount=Counter(t['campaign']['root_family'] for t in tasks)
    assert len(tasks)==480 and len(famcount)==240 and set(famcount.values())=={2}
    assert Counter(t['derivation']['recipe_id']+'|'+t['morphology']['lakara']+'|'+t['morphology']['prayoga'] for t in tasks)==Counter(p['cell_counts'])
    assert Counter(t['dhatu']['gana'] for t in tasks)==Counter(p['gana_counts'])
    assert len({t['id'] for t in tasks})==480
    audit=validate(tasks,'development');atomic_json(output,tasks);atomic_json(OUT/'pilot-04.prompts.json',prompts);atomic_json(OUT/'pilot-04.runner-audit.json',audit)
    manifest=json.loads((OUT/'pilot-04.provisional.manifest.json').read_text());manifest.update(frozen_at=now(),prompt_version=VERSION,
      task_file_sha256=sha(output),finalizer_sha256=sha(Path(__file__)),shared_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),
      renderer_sha256=sha(ROOT/'misc/vp_cartesian_prompt_v3.py'),renderer_fields_sha256=sha(ROOT/'misc/vp_sanskrit_prompt_v1.py'),
      oracle_policy='oracle-policy-10',original_provisional_sha256=oldhash,revision_audit_sha256=sha(OUT/'pilot-04.revision-01.audit.json'),
      new_families_vs_prior_five_d_panels=len(families-pilotfamilies),reused_families_vs_prior_five_d_panels=len(families&pilotfamilies),
      families_absent_from_all_historical_inputs=len(families-historyfamilies),families_present_in_all_history=len(families&historyfamilies),
      lexical_vowels=dict(Counter(''.join(c for c in t['campaign']['lexical_bases'][0] if c in VOWELS) for t in tasks)),
      gold_variants=dict(Counter(len(t['gold_slp1']) for t in tasks)),
      all_ledger_tuple_overlap_count=0,status='Frozen; ready for coordinator review and paired reference submissions. No worker paid calls.')
    atomic_json(OUT/'pilot-04.manifest.json',manifest)
    atomic_json(OUT/'pilot-04.final-novelty-audit.json',{'created_at':now(),'task_file_sha256':sha(output),'ledgers':ledgerhashes,'inputfiles':inputfiles,
      'normalized_unique_historical_tuples':len(historical),'overlap_count':0,'normalization':'Same citation/gana, no prefix, no specified pada, same ordered operations and all four coordinates; recurse historical forms.','answers_read_for_selection':False})
    prompt_audit={'created_at':now(),'renderer':str(ROOT/'misc/vp_cartesian_prompt_v3.py'),'renderer_sha256':sha(ROOT/'misc/vp_cartesian_prompt_v3.py'),
      'supporting_fields_renderer_sha256':sha(ROOT/'misc/vp_sanskrit_prompt_v1.py'),'independent_read_completed':True,
      'fields_checked':['Full citation with anubandha markers; same Devanagari transliteration function','All ten gana names map to the same dictionary classes','Traditional artha retained verbatim through transliteration','All four coordinates map to correct Sanskrit names','Exactly one ordered recipe; first-listed operation explicitly applies first','One valid Devanagari form inside answer tags, no additional text','No prefix or separately selected pada field'],
      'semantic_equivalence':'Input grammar and acceptable-output task are unchanged. English glosses and class numerals are replaced by exact Sanskrit grammatical names; language is an elicitation change and may affect measured difficulty.',
      'diagnostic_basis':'Coordinator36-question enriched paired probe: Sanskrit2refusals versus7in each English arm;27 previously completed controls give25correct and0refusals in Sanskrit. This is not an unbiased population accuracy estimate or a universal refusal fix.',
      'comparison_limit':'Reweighting pilot04 to pilot03 grammar weights is an original-mixture estimate under v3; comparing it with historical v1 cannot isolate the causal effect of grammar weights.',
      'prompt_file':str(OUT/'pilot-04.prompts.json'),'prompt_file_sha256':sha(OUT/'pilot-04.prompts.json')}
    atomic_json(OUT/'pilot-04.prompt-audit.json',prompt_audit)
    request={'created_at':now(),'track':'five_d','label':'five-d-pilot-04','n':480,'phase':'fresh_development_confirmation',
      'status':'ready_for_coordinator_review_not_submitted','task_file':str(output),'task_file_sha256':sha(output),'split':'development',
      'references':[{'provider':'Anthropic','model':'Opus5.5'},{'provider':'OpenAI','model':'Astra'}],
      'reasoning_effort':'xhigh','max_output_tokens':16384,'prompt_version':VERSION,'task_type':'cartesian_5d','oracle_policy':'oracle-policy-10',
      'plan':str(OUT/'pilot-04.plan.json'),'manifest':str(OUT/'pilot-04.manifest.json'),'audit':str(OUT/'pilot-04.runner-audit.json'),
      'prompt_audit':str(OUT/'pilot-04.prompt-audit.json'),'novelty_audit':str(OUT/'pilot-04.final-novelty-audit.json'),
      'analysis_predeclaration':str(OUT/'pilot-04.analysis-predeclaration.json'),'comparison_language_caveat':prompt_audit['comparison_limit'],
      'worker_paid_calls':0,'spending_authority':'Coordinator only under shared cumulative caps.','benchmark_ready':False}
    atomic_json(OUT/'pilot-04.experiment-request.json',request)
    status('Fresh paired confirmation frozen','Frozen 480 new questions under policy10 and Sanskrit prompt v3. One two-question Divadi family was replaced by the seeded same-cell rule; original provisional inputs remain unchanged. Full shared validation and both-ledger novelty checks pass. The coordinator owns all submissions and spending.')
    print(json.dumps({'request':request,'replacements':replacement},indent=2))

if __name__=='__main__':main()
