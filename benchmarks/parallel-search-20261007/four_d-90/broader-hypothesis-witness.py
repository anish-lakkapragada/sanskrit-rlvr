"""Input-only feasibility witness; no frozen task panel or provider request."""
import json,sys,hashlib
from pathlib import Path
from collections import defaultdict,Counter
ROOT=Path.cwd();OUT=ROOT/'benchmarks/parallel-search-20261007/four_d-90'
sys.path.insert(0,str(ROOT/'benchmarks/parallel-search-20261006/four_d/_solver_deps'));import highspy
rs=[r for r in json.loads((OUT/'broader-hypothesis-metadata.json').read_text()) if r['split']=='development' and not r['prior_exact_input']]
rs.sort(key=lambda r:hashlib.sha256(('broader-ending-20261007:'+r['id']).encode()).hexdigest())
h=highspy.Highs();h.setOptionValue('output_flag',False);h.setOptionValue('time_limit',20.0);h.setOptionValue('threads',2)
x=[h.addVariable(lb=0,ub=1,type=highspy.HighsVarType.kInteger) for r in rs];maps={k:defaultdict(list) for k in ['cell','family','gana','lakara']}
for i,r in enumerate(rs):
 for k in maps:maps[k][r[k]].append(x[i])
h.addConstr(h.qsum(x)==96)
for v in maps['cell'].values():h.addConstr(h.qsum(v)==24)
for v in maps['family'].values():h.addConstr(h.qsum(v)<=1)
for g,v in maps['gana'].items():
 h.addConstr(h.qsum(v)>=1);h.addConstr(h.qsum(v)<=(48 if g=='Bhvadi' else 24 if g=='Curadi' else 16))
for la in ['Lan','Lrn','VidhiLin','AshirLin']:h.addConstr(h.qsum(maps['lakara'][la])==12)
h.minimize(h.qsum((i+1)*v for i,v in enumerate(x)));sol=h.getSolution();chosen=[r for r,v in zip(rs,x) if sol.value_valid and sol.col_value[int(v)]>.5]
a=dict(feasible=len(chosen)==96,status=str(h.getModelStatus()),n=len(chosen),families=len({r['family'] for r in chosen}),classes=dict(Counter(r['gana'] for r in chosen)),tenses=dict(Counter(r['lakara'] for r in chosen)),cells=dict(Counter(r['cell'] for r in chosen)),membership_is_unpaid_metadata_witness_not_frozen_tasks=True)
(OUT/'broader-hypothesis-witness.json').write_text(json.dumps(dict(summary=a,metadata=chosen),ensure_ascii=False,indent=2)+'\n');print(a)
