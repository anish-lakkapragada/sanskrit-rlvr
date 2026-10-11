"""Offline ciN pilot source/control receipt. Never reads provider results."""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from misc.vp_cartesian_task import GRAMMAR, entries_by_code, validate_task
from misc.vp_cartesian_prompt_v1 import render
from vidyut.prakriya import DhatuPada, Lakara, Pada, Prayoga, Purusha, Vacana

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'benchmarks/parallel-search-20261006/four_d/coverage-gap-06'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, obj):
    p = OUT/name
    assert not p.exists(), f'Preserve existing receipt: {p}'
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')


def derive(entry, m, pada=None):
    return GRAMMAR.derive(Pada.Tinanta(dhatu=entry.dhatu,
        lakara=getattr(Lakara,m['lakara']), prayoga=getattr(Prayoga,m['prayoga']),
        purusha=getattr(Purusha,m['purusha']), vacana=getattr(Vacana,m['vacana']),
        dhatu_pada=pada))


def paths(ps):
    return [dict(text=p.text, history=[dict(rule=h.code,source=str(h.source).split('.')[-1],
        terms=h.result) for h in p.history]) for p in ps]


def branch(t):
    rules=set(t['campaign']['trace_rule_ids'])
    for rule,label in [('7.3.33','A_final_yuk'),('7.2.116','penultimate_a_vrddhi'),
                       ('7.3.86','ik_guna')]:
        if rule in rules:return label
    return 'other_cin_base'


def main():
    tasks=json.loads((OUT/'cin-candidate-inputs.json').read_text())
    es=entries_by_code(); controls=[]; rows=[]
    split=json.loads((ROOT/'benchmarks/creation-campaign-20261006/family-split.json').read_text())['families']
    for t in tasks:
        e=es[t['dhatu']['code']]
        assert split[t['campaign']['root_family']]['split']=='development'
        validate_task(t,e,'development')
        ps=derive(e,t['morphology'])
        unrestricted={p.text for p in ps}
        explicit={p.text for pada in DhatuPada.choices() for p in derive(e,t['morphology'],pada)}
        assert unrestricted==explicit==set(t['gold_slp1'])
        assert all({'3.1.66','6.4.104'} <= {h.code for h in p.history} for p in ps)
        assert '6.4.92' not in t['campaign']['trace_rule_ids']
        assert hashlib.sha256(render(t).encode()).hexdigest()==t['campaign']['prompt_sha256']
        rows.append(dict(id=t['id'],family=t['campaign']['root_family'],code=e.code,
            gana=t['dhatu']['gana'],branch=branch(t),gold=t['gold_slp1'],
            path_count=len(ps),pada_union_equal=True,all_paths_mandatory_cin=True))
        controls.append(dict(kind='panel_positive',id=t['id'],code=e.code,
            morphology=t['morphology'],branch=branch(t),derivations=paths(ps)))
    # Meaning unchanged. Each negative toggles one supplied inflection coordinate only.
    for code in ['04.0013','05.0007','09.0044','10.0221']:
        base=dict(lakara='Lun',prayoga='Karmani',purusha='Prathama',vacana='Eka')
        for key,value in [('vacana','Dvi'),('lakara','Lat'),('prayoga','Kartari')]:
            m=dict(base,**{key:value});ps=derive(es[code],m)
            assert ps and all('3.1.66' not in {h.code for h in p.history} for p in ps)
            controls.append(dict(kind='one_coordinate_negative',code=code,
                morphology=m,derivations=paths(ps)))
    rules=['1.3.13','3.1.55','3.1.66','3.1.67','6.4.24','6.4.51','6.4.72','6.4.93',
           '6.4.104','7.2.115','7.2.116','7.3.33','7.3.86','6.1.96','8.2.23']
    sd=OUT/'primary-sources';sd.mkdir(exist_ok=True)
    def source(rule):
        url=f'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/{rule[0]}/{rule}.htm'
        p=sd/'browser-receipt.json'
        return dict(rule=rule,url=url,browser_receipt=str(p.relative_to(OUT)),sha256=sha(p),
            cache_scope='Web-tool rendered primary text receipt, not raw server HTML.')
    sources=list(map(source,rules))
    for name in ['source-02/dhatupatha.txt','source-03/dhatupradipa-clean.txt']:
        p=OUT.parent/name
        sources.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),
            use='Previously saved primary dictionary text; source identity and transitivity corroboration, not a printed proof of every paradigm.'))
    save('cin-source-controls.json',controls)
    save('cin-branches.json',rows)
    save('cin-source-receipt.json',dict(created_at=datetime.now(timezone.utc).isoformat(),
        tasks_sha256=sha(OUT/'cin-candidate-inputs.json'),
        script_sha256=sha(Path(__file__)),controls_sha256=sha(OUT/'cin-source-controls.json'),
        branches_sha256=sha(OUT/'cin-branches.json'),sources=sources,
        n=len(tasks),families=len({r['family'] for r in rows}),
        gana_counts=dict(Counter(r['gana'] for r in rows)),
        branch_counts=dict(Counter(r['branch'] for r in rows)),
        positive_paths=sum(r['path_count'] for r in rows),negative_controls=12,
        full_regeneration_pass=True,master_development_split_pass=True,
        explicit_pada_union_pass=True,all_paths_mandatory_cin_pass=True,
        mit_shortening_6_4_92_contexts=0,
        full_accepted_unions_preserved=True,no_paid_calls=True,no_results_read=True,
        benchmark_ready=False))
    print(json.dumps(dict(n=len(rows),ganas=dict(Counter(r['gana'] for r in rows)),
        branches=dict(Counter(r['branch'] for r in rows)),task_sha=sha(OUT/'cin-candidate-inputs.json'))))


if __name__=='__main__':main()
