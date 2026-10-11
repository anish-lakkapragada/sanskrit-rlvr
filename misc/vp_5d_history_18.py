"""History for pre-exposure pilot07 revision: explicitly account for revoked inputs."""
import json
from collections import Counter
from misc.vp_5d_prepare_04 import ROOT,sha
from misc.vp_5d_novelty_04 import normalized,walk

REVOKED={'opus-five-d-pilot-07-a','opus-five-d-pilot-07-b'}

def history():
    seen=set();families=set();files=[];ledgers=[];counts=Counter();revoked=[]
    for directory in ['creation-campaign-20261006','iterative-goal-20261006']:
        lp=ROOT/'benchmarks'/directory/'ledger.json';ledger=json.loads(lp.read_text())
        ledgers.append({'path':str(lp),'sha256':sha(lp)})
        for name,job in ledger['jobs'].items():
            path=lp.parent/'jobs'/name/'tasks.json';tasks=json.loads(path.read_text())
            if name in REVOKED:
                assert job.get('attempted_at') is None and job.get('batch_id') is None
                assert job.get('reservation_micro',0)==0
                assert job['status']=='unsubmitted_oracle_review_hold'
                revoked.append(dict(job=name,path=str(path),sha256=sha(path),n=len(tasks),attempted_at=None,batch_id=None,reservation_micro=0,reason='Explicitly preserved unsubmitted predecessor of this source-driven revision; report overlap separately.'))
                continue
            files.append(dict(path=str(path),sha256=sha(path),top_level_tasks=len(tasks)))
            for task in tasks:
                for row in walk(task):
                    counts['records']+=1;sig,issue=normalized(row)
                    if issue:counts[issue]+=1
                    else:seen.add(sig);counts['matching_shape_records']+=1
                    family=row.get('campaign',{}).get('root_family')
                    if family:families.add(family)
    assert {x['job'] for x in revoked}==REVOKED
    return seen,families,dict(ledgers=ledgers,task_files=files,counts=dict(counts),unique_matching_tuples=len(seen),unsubmitted_predecessor_records_separately_accounted=revoked)
