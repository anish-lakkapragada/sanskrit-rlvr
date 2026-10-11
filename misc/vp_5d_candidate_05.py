"""Exploratory joint-cell design contrasts; no membership or paid calls."""
from __future__ import annotations
import json, math
from collections import Counter, defaultdict
import numpy as np
from misc.vp_5d_prepare_04 import OUT, ROOT, RECIPES, status, atomic_json, now, sha
from misc.vp_5d_release_feasibility import MinCost, apportion
from misc.vp_5d_audit_03 import current_issue
from misc.vp_5d_calibration_analysis_02 import summarize
from misc import vp_campaign_candidates as old

def quotas(lun,passive):
    oldplan=json.loads((OUT/'pilot-04.plan.json').read_text())
    tense={'Lun':lun,**apportion({l:n for l,n in oldplan['lakara_counts'].items() if l!='Lun'},480-lun)}
    recipes=oldplan['recipe_counts'];joint={};net=MinCost();edges=[]
    # Controlled rounding of an independent recipe x tense design.
    for r,n in recipes.items():
        q=sum(math.floor(n*v/480) for v in tense.values());net.edge('s',('r',r),n-q)
    for l,n in tense.items():
        q=sum(math.floor(n*v/480) for v in recipes.values());net.edge(('l',l),'t',n-q)
    for r,nr in recipes.items():
        for l,nl in tense.items():
            ideal=nr*nl/480;joint[(r,l)]=math.floor(ideal)
            edges.append((r,l,net.edge(('r',r),('l',l),1,round(10000*(1-(ideal-math.floor(ideal)))))))
    need=480-sum(joint.values());assert net.flow('s','t',need)[0]==need
    for r,l,e in edges:joint[(r,l)]+=e[3]-e[1]
    pas=apportion({c:n for c,n in oldplan['cell_counts'].items() if c.endswith('|Karmani')},passive)
    cells={}
    for (r,l),n in joint.items():
        p=pas.get(r+'|'+l+'|Karmani',0);assert p<=n
        cells[r+'|'+l+'|Kartari']=n-p
        if p:cells[r+'|'+l+'|Karmani']=p
    assert sum(cells.values())==480
    return {'n':480,'recipe_counts':recipes,'lakara_counts':tense,'passive_count':passive,'cell_counts':cells}

def estimate(rows,design,coarse=False):
    def key(t):
        r=t['derivation']['recipe_id'];m=t['morphology'];la=m['lakara']
        return '|'.join((r,('aorist' if la=='Lun' else 'other') if coarse else la,m['prayoga']))
    groups=Counter(key(r['task']) for r in rows);target=Counter()
    for c,n in design['cell_counts'].items():
        rec,la,v=c.split('|');target['|'.join((rec,('aorist' if la=='Lun' else 'other') if coarse else la,v))]+=n
    assert set(target)<=set(groups)
    cs=defaultdict(lambda:np.zeros(3))
    for r in rows:
        t=r['task'];w=target[key(t)]/groups[key(t)];complete=r['status']=='completed'
        cs[t['campaign']['root_family']]+=w*np.array([int(complete and bool(r['is_correct'])),int(complete),1])
    a=np.array(list(cs.values()));g=len(a);boot=np.random.default_rng(202610070705).multinomial(g,[1/g]*g,10000);out={}
    for label,col in [('all_requests',2),('completed',1)]:
        p=a[:,0].sum()/a[:,col].sum();u=a[:,0]-p*a[:,col]
        z=(boot@a[:,0])/(boot@a[:,col]);out[label]={'accuracy':float(p),'cluster_se':math.sqrt(g/(g-1)*(u@u))/a[:,col].sum(),'bootstrap_percentile95':np.quantile(z,[.025,.975]).tolist()}
    out['standardization_cells']=len(target);out['smallest_observed_cell']=min(groups[c] for c in target)
    return out

def main():
    path=ROOT/'benchmarks/iterative-goal-20261006/jobs/opus-five-d-pilot-04/results.json';rs=json.loads(path.read_text());es={e.code:e for e in old.load_entries()}
    rs=[r for r in rs if not current_issue(r['task'],es)]
    baseline=json.loads((OUT/'pilot-04.plan.json').read_text());designs={'pilot04_original':baseline}
    for l in [144,168,192]:designs[f'Lun{l//48*10 if l%48==0 else 35}_passive10']=quotas(l,48)
    groups=defaultdict(list)
    for r in rs:
        t=r['task'];m=t['morphology'];c='|'.join((t['derivation']['recipe_id'],m['lakara'],m['prayoga']));groups[c].append(r)
    out={'created_at':now(),'policy':'oracle-policy-11','source_sha256':sha(path),'shared_adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),
        'current_summary':summarize(rs),'joint_cells':{c:summarize(v) for c,v in groups.items()},
        'contrasts':{name:{'design':d,'fine_joint_standardization':estimate(rs,d),'coarse_recipe_aorist_voice_standardization':estimate(rs,d,True)} for name,d in designs.items()},
        'reason':'Retain all three recipe proportions and the relative distribution of the other nine lakaras. Contrast fewer passive questions at fixed30% Lun, then35% and40% Lun. This isolates broad levers without fitting rare-root or tiny subcell errors.',
        'grammar_sources':{'passive_atmanepada':'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/1/1.3.13.htm','passive_yak':'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.67.htm','active_causal_aorist':'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.48.htm'},
        'grammar_interpretation':'Voice changes the finite derivation, not an extra task coordinate: Karmani selects atmanepada, and sarvadhatuka passives add yak, whereas Kartari causal Lun has the distinct can/reduplication environment. Intensive stem preservation and suffix ordering therefore occur in different contexts. The sources support this contrast; they do not prove passive forms must be easier for a model. All original passives lie outside Lun, so a marginal voice contrast is confounded.',
        'limitations':['Exploratory development reweighting, not an independent score or qualification; confidence intervals omit design adaptation and oracle uncertainty.',
          'Fine recipe/tense/voice cells are small. Coarse standardization pools non-aorist tenses and is a sensitivity assumption, not a second independent test.',
          'Keep all-request, completed and missing-response bounds parallel. Refusals cannot be the reason a target is met.',
          'No final membership or question selection is made here. A new frozen seeded development panel is required.'],
        'no_final_membership_selected':True,'no_heldout_answers_read':True,'paid_calls':0}
    atomic_json(OUT/'pilot-05.candidate-comparison.json',out)
    print(json.dumps({k:{'lakaras':v['design']['lakara_counts'],'fine':v['fine_joint_standardization'],'coarse':v['coarse_recipe_aorist_voice_standardization']} for k,v in out['contrasts'].items()},indent=2))

if __name__=='__main__':main()
