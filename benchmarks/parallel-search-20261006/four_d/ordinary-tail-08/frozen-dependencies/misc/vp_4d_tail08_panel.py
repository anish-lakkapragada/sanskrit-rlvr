"""Fixed input-only breadth panel from never-yet-xHigh-screened dev families."""
import hashlib,json
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path

from vidyut.prakriya import DhatuPada,Lakara,Pada,Prayoga,Purusha,Vacana
from misc.vp_cartesian_task import GRAMMAR,entries_by_code,make_task,validate_task
from misc.vp_4d_coverage05 import COORDS,issue,repeat_mechanism,metadata

ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'benchmarks/parallel-search-20261006/four_d'
OUT=B/'ordinary-tail-08'
SEED='ordinary-tail-08-v1'
CLASSES=dict(Bhvadi=48,Curadi=24,Tudadi=12,Divadi=6,Adadi=3,Kryadi=3)
LAKARAS=['Lat','Lut','Lrt','Lan','VidhiLin','AshirLin','Lun','Lrn']
PURUSHA=['Prathama','Madhyama','Uttama'];VACANA=['Eka','Dvi','Bahu']


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def rank(s):return hashlib.sha256((SEED+'|'+s).encode()).hexdigest()
def save(n,d):
    p=OUT/n;assert not p.exists();p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')


def matching(left,slots,allowed,label):
    """Deterministic augmenting-path perfect matching; no external solver."""
    owners={}
    def augment(f,seen):
        for j in sorted(range(len(slots)),key=lambda j:rank(label+'|'+f+'|'+str(j))):
            if j in seen or not allowed(f,slots[j]):continue
            seen.add(j)
            if j not in owners or augment(owners[j],seen):owners[j]=f;return True
        return False
    for f in sorted(left,key=rank):
        if not augment(f,set()):return None
    return {f:slots[j] for j,f in owners.items()}


def main():
    rows=read(OUT/'fresh-tail-metadata.json')
    pending={t['campaign']['root_family'] for t in read(B/'coverage-gap-06/cin-candidate-inputs.json')}
    rows=[r for r in rows if r['family'] not in pending]
    byfamily=defaultdict(list)
    for r in rows:byfamily[r['family']].append(r)
    selected=[]
    for gana,n in CLASSES.items():
        fs=sorted((f for f,rr in byfamily.items() if rr[0]['gana']==gana),key=rank)
        assert len(fs)>=n
        selected+=fs[:n]
    assert len(selected)==len(set(selected))==96
    pn={(p,v):10 if i==j else 11 for i,p in enumerate(PURUSHA)for j,v in enumerate(VACANA)}
    design=dict(created_at=datetime.now(timezone.utc).isoformat(),seed=SEED,n=96,
        input_only=True,current_reference_family_coverage='No question from these exact citation+gana families occurred in any of the six completed eligible xHigh probes. Exclude all46 pending ciN families as well; no outcomes read.',
        domain='Classical ordinary Kartari,8lakaras excluding allLot/Lit and prior adanta/dhvam/specialized-it/Kutadi contexts; no chosen pada, prefixes or added derivations.',
        family_selection='Independent SHA256 family ranking within six fixed class quotas, before coordinate allocation. Exactly one question per family. No accuracy, gold surface or engine complexity objective.',
        class_counts=CLASSES,lakara_counts=dict.fromkeys(LAKARAS,12),
        person_number_counts={'|'.join(k):v for k,v in pn.items()},
        quota_rationale='Breadth diagnostic: equal eight-tense mass and balanced person/number; capBhvadi at50% andCuradi25%. These are prospective experiment choices, not user-mandated final quotas or unbiased population weights.',
        coordinate_selection='Deterministic augmenting-path family-to-tense matching followed by family/tense-to-PN matching. Use the first feasible hash-labeled attempt in0..99. Exact historical tuples are already removed; no accuracy or complexity optimization.',
        reference=dict(model='claude-opus-5-5',effort='xhigh',max_output_tokens=65536,prompt_version='cartesian-4d-v1'),
        exploratory_trigger=dict(minimum_usable=90,minimum_wrong_completed_families=16,minimum_error_ganas=3,minimum_error_lakaras=4,
            interpretation='A distributed broad-tail error signal motivates later grammar-defined stratification and independent confirmation, not release or failed-item promotion. No observed hardness is assumed.'),
        limits=['Six classes, not allten: four classes have no completely untested development family in this conservative domain.','Some selected families have older High/4096 or other input exposure; never-current-xHigh is not globally-unseen.','AllKartari; voice expansion requires separate source-supported passive transitivity controls.','N96 has nominal iidSE about4.2pp at79%, not final<1pp precision.','No pairedAstra, payment or final membership authorized.'],benchmark_ready=False)
    save('panel-design.json',design)
    options=defaultdict(dict)
    for f in selected:
        for r in sorted(byfamily[f],key=lambda r:rank(r['id'])):
            options[f].setdefault((r['lakara'],r['purusha'],r['vacana']),r)
    for attempt in range(100):
        lm=matching(selected,[l for l in LAKARAS for _ in range(12)],
            lambda f,l:any(k[0]==l for k in options[f]),'tense:'+str(attempt))
        assert lm is not None
        pm=matching(selected,[pv for pv,n in pn.items() for _ in range(n)],
            lambda f,pv:(lm[f],*pv) in options[f],'pn:'+str(attempt))
        if pm is not None:break
    assert pm is not None,'No predeclared matching attempt was feasible'
    take=[options[f][(lm[f],*pm[f])] for f in selected];assert len(take)==96
    es=entries_by_code();tasks=[];audit=[];traces=[]
    for r in sorted(take,key=lambda r:rank(r['id'])):
        e=es[r['code']];t=make_task(e,'development',{k:r[k] for k in COORDS})
        validate_task(t,e,'development');assert not issue(t,e) and not repeat_mechanism(metadata(t))
        def derive(pada=None):return GRAMMAR.derive(Pada.Tinanta(dhatu=e.dhatu,lakara=getattr(Lakara,r['lakara']),prayoga=Prayoga.Kartari,purusha=getattr(Purusha,r['purusha']),vacana=getattr(Vacana,r['vacana']),dhatu_pada=pada))
        ps=derive();gold={p.text for p in ps};pg={p.text for pada in DhatuPada.choices() for p in derive(pada)}
        assert gold==pg==set(t['gold_slp1'])
        tasks.append(t);audit.append(dict(id=t['id'],family=r['family'],gana=r['gana'],lakara=r['lakara'],explicit_pada_union_equal=True,accepted_paths=len(ps),gold_variants=len(gold)))
        traces.append(dict(id=t['id'],code=e.code,derivations=[dict(text=p.text,history=[dict(rule=h.code,source=str(h.source),terms=h.result)for h in p.history])for p in ps]))
    save('panel.questions.json',tasks);save('panel-source-paths.json',traces)
    save('panel-mechanical-audit.json',dict(created_at=datetime.now(timezone.utc).isoformat(),tasks_sha256=sha(OUT/'panel.questions.json'),script_sha256=sha(Path(__file__)),design_sha256=sha(OUT/'panel-design.json'),
        n=96,families=96,class_counts=dict(Counter(t['dhatu']['gana']for t in tasks)),lakara_counts=dict(Counter(t['morphology']['lakara']for t in tasks)),
        PN_counts=dict(Counter('|'.join([t['morphology']['purusha'],t['morphology']['vacana']])for t in tasks)),accepted_union_sizes=dict(Counter(len(t['gold_slp1'])for t in tasks)),
        all_regeneration_and_pada_checks_pass=True,matching_attempt=attempt,checks=audit,benchmark_ready=False))
    print('Panel SHA',sha(OUT/'panel.questions.json'))
    print('Variants',Counter(len(t['gold_slp1'])for t in tasks))


if __name__=='__main__':main()
