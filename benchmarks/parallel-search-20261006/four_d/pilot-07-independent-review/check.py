"""Independent bounded ciN input/source-control check; no provider records."""
from pathlib import Path
import copy,hashlib,json,sys
from collections import Counter
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from misc.vp_cartesian_task import entries_by_code,entry_scope_issue,oracle_issue,GRAMMAR
from misc.vp_goal_validate import validate
from misc.vp_cartesian_prompt_v1 import render
from vidyut.prakriya import DhatuPada,Lakara,Pada,Prayoga,Purusha,Vacana,Sanadi
OUT=Path(__file__).resolve().parent
SRC=ROOT/'benchmarks/parallel-search-20261006/four_d/coverage-gap-06'
COORDS=('lakara','prayoga','purusha','vacana')
def read(p):
    assert p.name!='results.json' and not p.name.endswith('.jsonl')
    return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,data):
    p=OUT/name;assert not p.exists();p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def derive(e,m,pada=None,ops=None):
    dhatu=e.dhatu if ops is None else e.dhatu.with_sanadi(ops)
    return GRAMMAR.derive(Pada.Tinanta(dhatu=dhatu,lakara=getattr(Lakara,m['lakara']),prayoga=getattr(Prayoga,m['prayoga']),purusha=getattr(Purusha,m['purusha']),vacana=getattr(Vacana,m['vacana']),dhatu_pada=pada))
def key(t):return (t['dhatu']['aupadeshika'],t['dhatu']['gana'],*(t['morphology'][k] for k in COORDS))
def ordinary(t):
    if not {'dhatu','morphology'}<=set(t) or not all(k in t['morphology'] for k in COORDS):return False
    d=t.get('derivation') or {}
    return not (d.get('sanadi') or d.get('prefixes') or any(x.get(k) for x in (t,t['dhatu'],t['morphology'],d) for k in ('pada','dhatu_pada')))
def main():
    source=SRC/'cin-candidate-inputs.json';assert sha(source)=='93b994f50b4f8ea898de49020f36fd685056ea018091826897803f5054f2e68a'
    tasks=read(source);assert len(tasks)==46
    es=entries_by_code();shared=validate(tasks,'development');rows=[]
    saved={c['id']:c for c in read(SRC/'cin-source-controls.json') if c['kind']=='panel_positive'}
    for t in tasks:
        e=es[t['dhatu']['code']];assert entry_scope_issue(e) is None and oracle_issue(t) is None
        assert set(t['morphology'])==set(COORDS) and t['morphology']==dict(lakara='Lun',prayoga='Karmani',purusha='Prathama',vacana='Eka')
        assert t['task_type']=='cartesian_4d' and 'derivation' not in t and not e.dhatu.prefixes and not e.dhatu.sanadi
        ps=derive(e,t['morphology']);gold={p.text for p in ps}
        by_pada={str(pada).split('.')[-1]:sorted({p.text for p in derive(e,t['morphology'],pada)}) for pada in DhatuPada.choices()}
        assert gold==set(t['gold_slp1'])==set().union(*(set(g) for g in by_pada.values()))
        paths=[]
        for p in ps:
            codes=[h.code for h in p.history];assert '3.1.66' in codes and '6.4.104' in codes and codes.index('3.1.66')<codes.index('6.4.104')
            h1=p.history[codes.index('3.1.66')];h2=p.history[codes.index('6.4.104')]
            assert 'ciR' in h1.result and 'ta' in h1.result and 'ta' not in h2.result
            paths.append(dict(form=p.text,cin_terms=h1.result,luk_terms=h2.result,passive_1_3_13_marker='1.3.13' in codes,rules=sorted(set(codes))))
        assert {p['text'] for p in saved[t['id']]['derivations']}==gold
        mutated=copy.deepcopy(t);mutated['gold_slp1']=['SENTINEL'];mutated['gold_devanagari']=['SENTINEL'];mutated['id']='SENTINEL';mutated['campaign']={}
        assert render(t)==render(mutated)
        rows.append(dict(id=t['id'],code=e.code,gana=t['dhatu']['gana'],meaning=e.artha,gold=sorted(gold),explicit_pada=by_pada,paths=paths,prompt_public_fields_only=True))
    negatives=[]
    for code in ['04.0013','05.0007','09.0044','10.0221']:
        for field,value in [('vacana','Dvi'),('lakara','Lat'),('prayoga','Kartari'),('purusha','Madhyama')]:
            m=dict(tasks[0]['morphology'],**{field:value});ps=derive(es[code],m)
            assert ps and all('3.1.66' not in {h.code for h in p.history} for p in ps)
            negatives.append(dict(code=code,changed_coordinate=field,morphology=m,gold=sorted({p.text for p in ps}),all_paths_without_3_1_66=True))
    # Printed source control outside the paid ordinary panel: single causal Sam, mit option.
    ps=derive(es['04.0098'],tasks[0]['morphology'],ops=[Sanadi.Ric])
    optional=dict(code='04.0098',operations=['Ric'],paid_panel_member=False,gold=sorted({p.text for p in ps}),source='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.93.htm',rules=sorted({h.code for p in ps for h in p.history}))
    assert set(optional['gold'])=={'aSami','aSAmi'} and '6.4.93' in optional['rules']
    nov=read(SRC/'cin-novelty-audit.json');history=set();counts=[];raw_records=0
    for item in nov['sources']:
        path=ROOT/item['path'];assert path.name in {'tasks.json','full-tasks.json'} or path.name.endswith('.questions.json'),str(path)
        assert sha(path)==item['sha256']
        prior=read(path);ks=[key(t) for t in prior if ordinary(t)]
        counts.append(dict(path=item['path'],sha256=item['sha256'],observed_records=len(ks),saved_records=item['ordinary_or_zero_operation_records']))
        history.update(ks);raw_records+=len(ks)
    overlap=[t['id'] for t in tasks if key(t) in history];assert not overlap
    save('mechanical-audit.json',dict(created_at=datetime.now(timezone.utc).isoformat(),task_sha256=sha(source),shared_validation=shared,n=46,families=len({t['campaign']['root_family'] for t in tasks}),gana_counts=dict(Counter(t['dhatu']['gana'] for t in tasks)),meaning_counts=dict(Counter(t['dhatu']['artha'] for t in tasks)),rows=rows,negative_controls=negatives,optional_control=optional,positive_path_count=sum(len(r['paths']) for r in rows),all_full_pada_unions_match=True,all_paths_mandatory_cin_luk=True,all_gold_variants_preserved=True,novelty=dict(source_files=len(counts),ordinary_records=raw_records,unique_normalized_inputs=len(history),overlap=overlap,records=counts,normalization='Citation+class+four coordinates, ignoring code/gloss; only no-prefix/no-added-operation/no-specified-pada inputs.'),no_model_results_read=True,no_paid_calls=True,benchmark_ready=False))
    print(json.dumps(dict(n=46,paths=sum(len(r['paths']) for r in rows),negatives=len(negatives),novelty_records=raw_records,source_files=len(counts),overlap=overlap,optional_control=optional['gold'])))
if __name__=='__main__':main()
