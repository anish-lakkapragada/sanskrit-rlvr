"""One-form passive creation from reviewed derived stems; no model calls."""
import hashlib
import random
from collections import Counter
import vidyut
from vidyut.prakriya import Pada, Prayoga, DhatuPada, Lakara, Purusha, Vacana, Sanadi, Vyakarana
from misc import vp_goal as c, vp_compositional as g, oai_batch_eval as io
from misc.vp_compositional_prompt_v4 import render
from misc.vp_goal_grammar import validate_prefixes

BASES = {'causative_of_intensive', 'desiderative_of_causative_of_intensive'}
LAKARAS = {'Lat','Lan','Lot','VidhiLin','Lit','Lut','Lrt','AshirLin'}
EXCLUDED_RULES = {'7.4.79','7.4.80','7.4.94','7.4.95','8.3.61'}


def task_for(entry, split, construction, prefixes, coordinates):
    validate_prefixes(prefixes)
    la,pu,va = coordinates
    if construction not in BASES or g.old.name(la) not in LAKARAS or g.old.name(entry.dhatu.gana)=='Curadi':
        raise ValueError('Unreviewed passive construction')
    ops = g.CONSTRUCTIONS[construction]
    d = entry.dhatu.with_sanadi([getattr(Sanadi,x) for x in ops]).with_prefixes(prefixes)
    ps = Vyakarana().derive(Pada.Tinanta(dhatu=d,prayoga=Prayoga.Karmani,lakara=la,
                           purusha=pu,vacana=va,dhatu_pada=DhatuPada.Atmanepada))
    gold = sorted({p.text for p in ps})
    rules = sorted({h.code for p in ps for h in p.history if g.old.name(h.source)=='Ashtadhyayi'})
    if not gold or len(gold)>64 or set(rules)&EXCLUDED_RULES:
        return None
    identity = [g.old.family(entry),ops,prefixes,'Karmani','Atmanepada',*map(g.old.name,coordinates)]
    t = {'id':'passive-'+c.digest(identity)[:24],'task_type':'passive_creation','prompt_version':'composition-v4-pada',
         'dhatu':{'code':entry.code,'aupadeshika':entry.dhatu.aupadeshika,'gana':g.old.name(entry.dhatu.gana),'artha':entry.artha},
         'morphology':{'lakara':g.old.name(la),'prayoga':'Karmani','purusha':g.old.name(pu),'vacana':g.old.name(va),'dhatu_pada':'Atmanepada'},
         'derivation':{'sanadi':ops,'prefixes':prefixes,'order':'innermost_to_outermost'},
         'gold_slp1':gold,'gold_devanagari':list(map(g.slp1_to_devanagari,gold)),
         'campaign':{'root_family':g.old.family(entry),'split':split,'construction':'passive_'+construction,
                     'base_construction':construction,'trace_rule_ids':rules,'minimum_trace_steps':min(len(p.history) for p in ps),
                     'gold_variants':len(gold),'vp_version':vidyut.__version__,
                     'selection_reason':'Passive voice crossed with a reviewed derived-stem chain; grammatical exclusions and random coordinates only.'}}
    for slp,deva in zip(gold,t['gold_devanagari']):
        if g.transliterate(deva,g.Scheme.Devanagari,g.Scheme.Slp1)!=slp:
            raise ValueError('Passive transliteration failed')
    t['campaign']['prompt_sha256']=hashlib.sha256(render(t).encode()).hexdigest()
    return t


def validate_task(t, entry, split):
    m=t['morphology']
    expected=task_for(entry,split,t['campaign']['base_construction'],t['derivation']['prefixes'],
                     (getattr(Lakara,m['lakara']),getattr(Purusha,m['purusha']),getattr(Vacana,m['vacana'])))
    if expected is None:
        raise ValueError('Passive task outside reviewed scope')
    for key,value in expected.items():
        if key=='campaign':
            if any(t[key].get(k)!=v for k,v in value.items()):
                raise ValueError('Passive metadata mismatch')
        elif t.get(key)!=value:
            raise ValueError('Passive regenerated data differs: '+key)
    cell=t['campaign'].get('sampling_cell',{})
    if cell and (m['lakara'] not in cell['lakaras'] or cell['base_construction']!=t['campaign']['base_construction']):
        raise ValueError('Passive sampling cell mismatch')


def generate(label, n_per_cell=16, seed=20261101):
    path=c.OUT/(label+'.json')
    if path.exists():
        raise ValueError('Passive panel already exists')
    assignment=io.read_json(c.HISTORY/'family-split.json')['families']
    entries={}
    for e in g.old.load_entries():
        if assignment[g.old.family(e)]['split']=='development' and g.old.name(e.dhatu.gana)!='Curadi':
            entries.setdefault(g.old.family(e),e)
    rng=random.Random(seed);used=set();tasks=[];cells=[]
    for base in sorted(BASES):
        for system,lakaras in [('present_system',['Lat','Lan','Lot','VidhiLin']),('other_tenses',['Lit','Lut','Lrt','AshirLin'])]:
            cell={'label':base+' / '+system,'base_construction':base,'lakaras':lakaras,'n':n_per_cell}
            cells.append(cell);count=0
            for _ in range(10):
                candidates=list(entries.items());rng.shuffle(candidates)
                for family,e in candidates:
                    if family in used:continue
                    t=task_for(e,'development',base,rng.choice([[],['pra'],['sam'],['vi'],['upa']]),
                               (getattr(Lakara,rng.choice(lakaras)),rng.choice(Purusha.choices()),rng.choice(Vacana.choices())))
                    if t is None:continue
                    t['campaign'].update(panel=label,sampling_cell=cell);tasks.append(t);used.add(family);count+=1
                    if count==n_per_cell:break
                if count==n_per_cell:break
            if count!=n_per_cell:raise ValueError('Insufficient passive supply')
    io.atomic_json(path,tasks)
    io.atomic_json(c.OUT/(label+'.sampling.json'),{'created_at':io.now(),'filename':path.name,'n':len(tasks),
        'root_families':len(used),'split':'development','seed':seed,'cells':cells,'task_digest':c.digest(tasks),
        'selection':'Shuffled distinct dhatu families, random grammatical coordinates. No model-score selection.',
        'exclusions':{'lakaras':['Lun','Lrn','Let'],'ganas':['Curadi'],'rules':sorted(EXCLUDED_RULES)}})
    return tasks
