"""Input-only full-census differences, no model responses."""
import json
from collections import Counter
from misc.vp_5d_prepare_04 import OUT,ROOT,now,sha,atomic_json

def main():
    out={}
    for label,stem in [('test','pilot-06.scale-supply-policy'),('development','development-confirmation-policy')]:
        suffix='.json' if label=='test' else '.supply.json'
        before=OUT/(stem+'17'+suffix);after=OUT/(stem+'18'+suffix)
        old=json.loads(before.read_text());new=json.loads(after.read_text())
        om={r['family']:r for r in old['rows']};nm={r['family']:r for r in new['rows']}
        assert set(om)==set(nm)
        removed=[];added=[]
        for family,row in om.items():
            masks=row['eligible_person_number_masks'];newm=nm[family]['eligible_person_number_masks']
            for cell in set(masks)|set(newm):
                a,b=masks.get(cell,0),newm.get(cell,0)
                if a&~b:removed.append(dict(family=family,cell=cell,removed_mask=a&~b,n=(a&~b).bit_count()))
                if b&~a:added.append(dict(family=family,cell=cell,added_mask=b&~a,n=(b&~a).bit_count()))
        assert not added
        out[label]=dict(before=str(before),before_sha256=sha(before),after=str(after),after_sha256=sha(after),removed_tuples=sum(x['n'] for x in removed),added_tuples=0,removed_cells=removed,affected_families=sorted({x['family'] for x in removed}))
    atomic_json(OUT/'pilot-06.supply-policy18-addendum.json',dict(created_at=now(),policy='oracle-policy-18',policy_sha256=sha(OUT.parent/'oracle-policy-18.json'),adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),census=out,method='Both full censuses regenerate every considered tuple under a fresh policy18 import; compare exact family/cell/PN masks. No model outcomes read.',paid_calls=0))
    print(json.dumps({k:{x:v[x] for x in ['removed_tuples','added_tuples','affected_families']} for k,v in out.items()},indent=2))

if __name__=='__main__':main()
