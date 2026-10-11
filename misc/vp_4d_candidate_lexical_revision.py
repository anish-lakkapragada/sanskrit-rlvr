"""Prospective source-only revision; preserve prior proposal and all retained keys."""
from collections import Counter
import copy
import json
from misc.vp_4d_candidate_prepare import BASE,ROOT,QUOTAS,rank
from misc.vp_4d_pilot import load_entries,family,name,identity,now,sha,write
from misc.vp_4d_pilot04 import COORDS,local_issue
from misc.vp_4d_pilot05 import short
from misc.vp_cartesian_task import make_task,validate_task,entry_scope_issue,oracle_issue
from misc.vp_cartesian_prompt_v1 import render

SOURCE=BASE/'candidate-1250-source-filtered'
OUT=BASE/'candidate-1250-v2'


def main():
    assert not (OUT/'tasks.json').exists(),'Preserve existing revision'
    previous=json.loads((SOURCE/'tasks.json').read_text())
    clarification=json.loads((BASE/'reading-clarification.json').read_text())
    assert clarification['reviewed_input']['sha256']==sha(SOURCE/'tasks.json')
    # Use only source-reviewed family membership. Neither selection nor freshness reads model answers.
    removed=[t for t in previous if t['dhatu']['code']=='10.0108' and
             t['campaign']['sampling_cell']['label']=='other_adanta_aorist']
    assert len(removed)==4 and {t['id'] for t in removed}=={t['id'] for t in clarification['affected_items']['10.0108']}
    chosen=[copy.deepcopy(t) for t in previous if t not in removed]
    families={t['campaign']['root_family'] for t in chosen if t['campaign']['sampling_cell']['label']=='other_adanta_aorist'}
    assert len(families)==21
    entries={e.code:e for e in load_entries()}
    inputs=sorted((ROOT/'benchmarks/iterative-goal-20261006/jobs').glob('*/tasks.json'))
    inputs+=sorted((ROOT/'benchmarks/creation-campaign-20261006/jobs').glob('*/tasks.json'))
    inputs+=[ROOT/'benchmarks/full-tasks.json',*sorted((ROOT/'benchmarks/creation-campaign-20261006').glob('discovery-??.json'))]
    def key(t):return (t['dhatu']['aupadeshika'],t['dhatu']['gana'],*(t['morphology'][k] for k in COORDS))
    prior=set()
    for path in inputs:
        for outer in json.loads(path.read_text()):
            for t in outer.get('forms',[outer]):
                if ('dhatu' in t and set(t.get('morphology',{}))==set(COORDS) and
                    not t.get('derivation',{}).get('sanadi') and not t.get('derivation',{}).get('prefixes')):
                    prior.add(key(t))
    occupied={key(t) for t in chosen};eligible=[]
    for e in entries.values():
        if family(e) not in families:continue
        assert name(e.dhatu.gana)=='Curadi' and not short(e) and not entry_scope_issue(e)
        for pu in ['Prathama','Madhyama','Uttama']:
            for va in ['Eka','Dvi','Bahu']:
                t=make_task(e,'test',dict(lakara='Lun',prayoga='Kartari',purusha=pu,vacana=va))
                if not t or oracle_issue(t) or local_issue(t) or key(t) in prior or key(t) in occupied:continue
                eligible.append(t)
    fc=Counter(t['campaign']['root_family'] for t in chosen)
    pc=Counter(t['morphology']['purusha'] for t in chosen)
    vc=Counter(t['morphology']['vacana'] for t in chosen)
    added=[]
    for _ in range(4):
        t=min(eligible,key=lambda t:(fc[t['campaign']['root_family']],pc[t['morphology']['purusha']]+vc[t['morphology']['vacana']],rank(t['id'])))
        eligible.remove(t)
        t['campaign'].update(panel='source-filtered-1250-proposal',
            sampling_cell={'label':'other_adanta_aorist','n':100},
            selection={'method':'Replace source-classification hold10.0108; balance remaining family/person/number, input-hash tie-break; no outcomes.'})
        chosen.append(t);added.append(t)
        fc[t['campaign']['root_family']]+=1;pc[t['morphology']['purusha']]+=1;vc[t['morphology']['vacana']]+=1
    for t in chosen:
        validate_task(t,entries[t['dhatu']['code']],'test')
        assert not oracle_issue(t) and not local_issue(t) and key(t) not in prior
    assert len(chosen)==len({identity(t) for t in chosen})==len({render(t) for t in chosen})==1250
    assert Counter(t['campaign']['sampling_cell']['label'] for t in chosen)==QUOTAS
    chosen.sort(key=lambda t:rank('order:'+t['id']))
    write(OUT/'tasks.json',chosen)
    write(OUT/'public-prompts.json',[{'id':t['id'],'prompt':render(t)} for t in chosen])
    write(OUT/'source-policy.json',{'created_at':now(),'previous_holds':json.loads((BASE/'test-source-hold-predeclaration.json').read_text()),
        'additional_exclusion':clarification['findings']['10.0108']['excluded_scope'],
        'additional_exclusion_reason':clarification['findings']['10.0108']['reason'],
        'retained_lexical_reading':clarification['findings']['10.0481']['public_declaration'],
        'clarification_sha256':sha(BASE/'reading-clarification.json'),
        'applies_uniformly_before_test_evaluation':True,'full_paradigm_certified':False})
    manifest=json.loads((SOURCE/'manifest.json').read_text())
    manifest.update(created_at=now(),version=2,families=len(fc),
        distribution={**{k:dict(Counter(t['morphology'][k] for t in chosen)) for k in COORDS},
                      'gana':dict(Counter(t['dhatu']['gana'] for t in chosen))},
        max_questions_per_family=max(fc.values()),
        inputs=[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in inputs],
        tasks_sha256=sha(OUT/'tasks.json'),public_prompts_sha256=sha(OUT/'public-prompts.json'),
        source_policy_sha256=sha(OUT/'source-policy.json'),
        previous_proposal_sha256=sha(SOURCE/'tasks.json'),source_classification_replacements=4,
        source_held_questions_replaced=16,source_held_codes=['10.0108','10.0430','10.0466','10.0467'],
        dependencies={**manifest['dependencies'],str(BASE.relative_to(ROOT))+'/reading-clarification.json':sha(BASE/'reading-clarification.json'),
                      'misc/vp_4d_candidate_lexical_revision.py':sha(__file__)},
        unresolved_before_final_freeze=['Strongest-reference comparison pending','Family-generalization SE below1pp unsupported',
            'Full accepted spelling/source policy and independent actual-miss adjudication remain required',
            'Final release reserve and spending registration not performed'],
        lexical_clarifications='Cada retained under two printed-source-supported literal-a reading; mArga excluded from adanta stratum. No keys patched.',
        paid_calls=0,test_model_answers_read=False,benchmark_ready=False)
    write(OUT/'manifest.json',manifest)
    write(OUT/'replacement-audit.json',{'created_at':now(),'removed_ids':[t['id'] for t in removed],
        'added_ids':[t['id'] for t in added],'retained_ids':1246,'retained_tasks_and_keys_unchanged':True,
        'all_inputs':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in inputs]})
    print(json.dumps({'n':len(chosen),'families':len(fc),'retained':1246,'added':len(added),'benchmark_ready':False}))


if __name__=='__main__':main()
