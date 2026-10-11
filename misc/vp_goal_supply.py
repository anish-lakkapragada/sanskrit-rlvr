"""Count available derived-root constructions without model calls."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hashlib,json
from collections import defaultdict
from misc import vp_goal as c,vp_compositional as g,oai_batch_eval as io
from vidyut.prakriya import Lakara,Purusha,Vacana
splits=io.read_json(c.HISTORY/'family-split.json')
test=sorted((f for f,a in splits['families'].items() if a['split']=='test'),key=lambda f:hashlib.sha256(('goal-reserve-v1:'+f).encode()).hexdigest())
reserve={'created_at':io.now(),'method':'score-independent SHA256 of goal-reserve-v1 + root family','initial_release_families':test[:500],'future_version_families':test[500:],'original_split_sha256':io.sha256(c.HISTORY/'family-split.json'),'note':'Both initial tiers may share families but must have disjoint tasks. Neither half has new model responses.'}
path=c.OUT/'test-family-reserve.json'
if path.exists():
 old=io.read_json(path)
 assert old['initial_release_families']==reserve['initial_release_families']
else:io.atomic_json(path,reserve)
entries={}
for e in g.old.load_entries():entries.setdefault(g.old.family(e),e)
stats=defaultdict(lambda:defaultdict(lambda:{'root_families':0,'sampled_coordinates':0,'nonempty_coordinates':0,'gold_form_count':0,'maximum_variants':0}))
for i,(f,e) in enumerate(entries.items()):
 split=splits['families'][f]['split']
 if split=='test':split='test_initial' if f in set(test[:500]) else 'test_reserve'
 for cell,ops in g.CONSTRUCTIONS.items():
  rec=stats[split][cell];nonempty=0
  for la in [v for v in Lakara.choices() if g.old.name(v)!='Let']:
   rec['sampled_coordinates']+=1
   ps=g.derive(e,ops,[],(la,Purusha.Prathama,Vacana.Eka))
   forms={p.text for p in ps}
   if forms:
    nonempty+=1;rec['nonempty_coordinates']+=1;rec['gold_form_count']+=len(forms);rec['maximum_variants']=max(rec['maximum_variants'],len(forms))
  rec['root_families']+=int(nonempty>0)
 if i%250==0:print('Census roots',i,flush=True)
io.atomic_json(c.OUT/'composition-supply.json',{'created_at':io.now(),'scope':'ten classical lakaras, third-person singular active, no prefixes; supply lower bound, not linguistic certification or difficulty evidence','strata':dict(stats)})
print(json.dumps(stats['test_initial'],indent=2),flush=True)
