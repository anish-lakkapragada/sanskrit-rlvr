"""Policy14 aggregate allocation witnesses, no final root membership export."""
import json,sys
from misc.vp_5d_prepare_04 import OUT,ROOT,atomic_json,status,now,sha
from misc.vp_5d_scale_witness_06 import witness

def main():
 source=OUT/'pilot-06.scale-supply-policy15.json';raw=json.loads(source.read_text());p=json.loads((OUT/'pilot-06.revision-01.plan.json').read_text());rows=raw['rows'];checks=[];designs=[]
 assert raw['shared_adapter_sha256']==sha(ROOT/'misc/vp_cartesian_task.py')
 for n in ([int(x) for x in sys.argv[1:]] or [2400,2880,3360,3840]):
  found=None
  for cap in range(3,16):
   for lcap in range(1,cap+1):
    r=witness(rows,p,n,cap,lcap,False);checks.append(r)
    if r['feasible']:found=(cap,lcap);break
   if found:break
  if not found:
   designs.append({'n':n,'feasible':False,'reason':'No feasible allocation through family cap15 with unique non-aorist tenses'});continue
  status('Quantifying policy15 repeated-aorist precision',f'Optimizing an input-only {n:,}-question45%-aorist allocation at family cap{found[0]} and aorist cap{found[1]}. No final membership or held-out model answers are selected.')
  r=witness(rows,p,n,*found,True);designs.append(r);atomic_json(OUT/f'pilot-06.scale-witness-policy15-N{n}.json',r);print(json.dumps(r),flush=True)
 rs={r:{row['family'] for row in rows if r+'|Lun|Kartari' in row['eligible_person_number_masks']} for r in p['recipe_counts']}
 out=dict(created_at=now(),policy='oracle-policy-15',source_sha256=sha(source),plan_sha256=sha(OUT/'pilot-06.revision-01.plan.json'),shared_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),recipe_supply=raw['recipe_supply'],accepted_tuples=raw['accepted_tuples'],aorist_supply_by_recipe={r:len(f) for r,f in rs.items()},nested_aorist_union_families=len(rs['causative_of_intensive']|rs['causative_of_intensive_luk']),capacity_checks=checks,balanced_designs=designs,limitations=['Exact input availability across the1000-family master test reserve, not an approved partition between tracks. Parent must prevent overlap with the other final track.','Source-control roots and unresolved stim/urja excluded; all462 RL families remain separately reserved.','SE scenarios assume common within-family correlation and constant Bernoulli variance. Neither measured Opus development correlation nor its confidence interval establishes final Astra correlation.','These aggregate flow witnesses export only counts; they do not select final question or family membership. All non-aorist tenses stay unique within a family.','Any chosen finalN must be frozen before final answers and pass both iid and cluster SE<1pp for both models.'],no_heldout_answers_read=True,no_final_membership_selected=True,benchmark_ready=False)
 atomic_json(OUT/('pilot-06.scale-analysis-policy15-extended.json' if sys.argv[1:] else 'pilot-06.scale-analysis-policy15.json'),out)
if __name__=='__main__':main()
