"""Independent input/synthetic checks only. Never read actual pilot08 outcomes."""
import hashlib
import itertools
import json
import math
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from misc import vp_5d_scale_after08 as target

ROOT=Path.cwd()
HERE=ROOT/'benchmarks/parallel-search-20261006/four_d/post08-scale-review-01'


def row(c,y,u):
    rec,la,pr=c.split('|')
    return dict(task=dict(derivation=dict(recipe_id=rec),morphology=dict(lakara=la,prayoga=pr)),
        is_correct=bool(y),status='completed' if u else 'refused',
        answer='a' if u else None,truncated=False)


def check():
    cells=['test|Lun|Kartari','test|Lat|Kartari','other|Lrt|Karmani']
    families=[[cells[0],cells[0],cells[1]],[cells[1],cells[2]],[cells[0]],
              [cells[0],cells[1],cells[2],cells[2]]]
    states=[(1,1),(0,1),(1,0),(0,0)]
    counts={cells[0]:[3,2,1,2],cells[1]:[1,3,2,2],cells[2]:[4,1,2,1]}
    rows=[row(c,*s) for c in cells for s,k in zip(states,counts[c]) for _ in range(k)]
    cnt=Counter(c for fs in families for c in fs)
    pairs=Counter(tuple(sorted((a,b))) for fs in families for a,b in itertools.combinations(fs,2))
    witness=dict(n=sum(cnt.values()),distinct_families=len(families),family_cap=4,
        aorist_per_family_cap=2,cell_counts=dict(cnt),
        unordered_within_family_cell_pair_counts=[dict(cell_a=a,cell_b=b,pairs=k) for (a,b),k in pairs.items()])
    checks=[]
    for prior in [0,.5]:
        m=target.moments(rows,witness,fine=True,prior=prior)
        prob={c:[(k+prior)/(sum(ks)+4*prior) for k in ks] for c,ks in counts.items()}
        p=sum(cnt[c]*sum(p*y for p,(y,u) in zip(prob[c],states)) for c in cells)/witness['n']
        q=sum(cnt[c]*sum(p*u for p,(y,u) in zip(prob[c],states)) for c in cells)/witness['n']
        theta=sum(cnt[c]*sum(p*y*u for p,(y,u) in zip(prob[c],states)) for c in cells)/(witness['n']*q)
        assert math.isclose(m['projected_all_accuracy'],p)
        assert math.isclose(m['projected_completion'],q)
        assert math.isclose(m['projected_usable_accuracy'],theta)
        for label in ['recorded_all_correct','completed_ratio_influence']:
            z=[float(y) if label=='recorded_all_correct' else u*(y-theta)/q for y,u in states]
            center=p if label=='recorded_all_correct' else 0
            mu={c:sum(a*b for a,b in zip(prob[c],z))-center for c in cells}
            var={c:sum(a*b*b for a,b in zip(prob[c],z))-(mu[c]+center)**2 for c in cells}
            direct_mean=sum(sum(mu[c] for c in fs)**2 for fs in families)
            direct_ind=sum(var[c] for fs in families for c in fs)
            direct_coef={k:sum(2*math.sqrt(var[a]*var[b]) for fs in families
                for a,b in itertools.combinations(fs,2) if target.category(a,b)==k) for k in target.CATEGORIES}
            got=m['estimates'][label]
            assert math.isclose(got['allocation_mean_squared_sum'],direct_mean,rel_tol=1e-12,abs_tol=1e-12)
            assert math.isclose(got['independent_variance_sum'],direct_ind,rel_tol=1e-12)
            assert all(math.isclose(got['pair_covariance_coefficients'][k],direct_coef[k],rel_tol=1e-12) for k in target.CATEGORIES)
            # Independent exact enumeration per family checks E[(sum z-centered)^2].
            expectation=0
            for fs in families:
                for states_i in itertools.product(range(4),repeat=len(fs)):
                    weight=math.prod(prob[c][i] for c,i in zip(fs,states_i))
                    residual=sum(z[i]-center for i in states_i)
                    expectation+=weight*residual**2
            assert math.isclose(expectation,direct_mean+direct_ind,rel_tol=1e-12)
            checks.append(dict(prior=prior,estimand=label,direct_mean=direct_mean,
                direct_independent=direct_ind,direct_pair_coefficients=direct_coef,
                exact_enumeration_second_moment=expectation,passed=True))
    # Eight independently pending jobs: real frozen input declaration, fake ledger.
    decl=json.loads((target.PANEL/'analysis-predeclaration.json').read_text())
    assert len(decl['expected_jobs'])==8
    guard=[]
    for pending in range(8):
        state=dict(jobs={e['id']:dict(e,phase='confirm_64k',settled=i!=pending,
            collected_at='synthetic' if i!=pending else None) for i,e in enumerate(decl['expected_jobs'])})
        paths=[]
        def fake_read(path):
            paths.append(str(path))
            if Path(path)==target.PANEL/'analysis-predeclaration.json':return decl
            if Path(path)==ROOT/'benchmarks/iterative-goal-20261006/ledger.json':return state
            raise AssertionError('Any further read is prohibited while a job remains pending')
        with patch.object(target.io,'read_json',side_effect=fake_read):
            try:target.analyze()
            except ValueError as e:assert str(e).startswith('All8jobs must settle')
            else:raise AssertionError('Pending job did not block')
        assert len(paths)==2
        guard.append(dict(pending_job=decl['expected_jobs'][pending]['id'],input_reads=2,outcome_reads=0,passed=True))
    return dict(synthetic_moment_cases=checks,all_eight_pending_positions=guard,
        actual_outcomes_read=False,shared_files_changed=False)


if __name__=='__main__':
    out=HERE/'synthetic-results.json';assert not out.exists()
    data=check();data['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print('Passed four direct/enumerated moment cases and eight pending-job guard cases.')
