#!/usr/bin/env python3
"""Family-disjoint, interpretable retrospective 4D difficulty diagnostic. Offline only."""
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc.vp_4d_pilot import OUT, HISTORY, TRANSITIVE_ARTHAS, load_entries, name, write, now, sha
from misc.vp_4d_pilot04 import local_issue
from misc.vp_4d_search03 import lexical_base
from misc.vp_cartesian_task import entry_scope_issue, oracle_issue
from vidyut.prakriya import Vyakarana

RUN_ID = 'overnight-surrogate-04'
SEEDS = [2026100704, 2026101704, 2026102704]
VOWELS = set('aAiIuUfFxXeEoO')
SHORT = set('aiufx')


def status(phase, message):
    write(OUT / 'status.json', dict(track='four_d', run_id=RUN_ID, state='running',
          updated_at=now(), phase=phase, message=message, benchmark_ready=False))
    with (OUT / 'progress.md').open('a') as f:
        f.write(f'\n- {now()}: {phase}: {message}\n')


def hnum(s):
    return int(hashlib.sha256(s.encode()).hexdigest()[:16], 16)


def sound_class(c):
    if c in VOWELS: return 'vowel'
    if c in 'NYRnm': return 'nasal'
    if c in 'yrlv': return 'semivowel'
    if c in 'Szsh': return 'sibilant_or_h'
    if c in 'kKgGcCjJwWqQtTdDpPbB': return 'stop'
    return 'other'


def features(t, entry, base):
    c = entry.dhatu.aupadeshika
    f = {f'gana={name(entry.dhatu.gana)}'}
    f |= {f'{k}={v}' for k, v in t['morphology'].items()}
    for label, flag in [('nasal_marker', '~' in c), ('anudatta', '\\' in c),
                        ('svarita', '^' in c), ('literal_final_a', c.endswith('a')),
                        ('initial_vowel', bool(base) and base[0] in VOWELS),
                        ('has_r', 'r' in base), ('has_v', 'v' in base),
                        ('consonant_cluster', any(a not in VOWELS and b not in VOWELS for a, b in zip(base, base[1:]))),
                        ('multiple_vowels', sum(x in VOWELS for x in base) >= 2)]:
        f.add(f'{label}={int(flag)}')
    f.add('citation_length=' + ('short' if len(c) <= 3 else 'medium' if len(c) <= 5 else 'long'))
    f.add('base_length=' + ('short' if len(base) <= 2 else 'medium' if len(base) <= 4 else 'long'))
    f.add('initial_class=' + sound_class(base[0] if base else ''))
    f.add('final_class=' + sound_class(base[-1] if base else ''))
    penult = base[-2] if len(base) > 1 else ''
    f.add('penultimate=' + ('short_vowel' if penult in SHORT else 'other_vowel' if penult in VOWELS else 'consonant_or_absent'))
    f |= {'trace=' + r for r in t['campaign']['trace_rule_ids'] if r and r[0].isdigit()}
    return sorted(f)


def load_data():
    es = {e.code: e for e in load_entries()}
    vy = Vyakarana()
    bases = {}
    data = {'xhigh': [], 'high': []}
    exclusions = defaultdict(Counter)
    sources = []
    paths = [(f'pilot{i:02d}', 'xhigh', ROOT / f'benchmarks/iterative-goal-20261006/jobs/opus-four-d-pilot-{i:02d}/results.json') for i in range(1, 6)]
    paths += [(f'historical{i:02d}', 'high', HISTORY / f'jobs/opus-discovery-{i:02d}/results.json') for i in range(1, 4)]
    for panel, fidelity, path in paths:
        # Only named development result files are opened. Check every embedded split before extracting labels.
        rows = json.loads(path.read_text())
        assert all(r['task']['campaign']['split'] == 'development' for r in rows)
        sources.append(dict(panel=panel, fidelity=fidelity, path=str(path.relative_to(ROOT)), sha256=sha(path)))
        for r in rows:
            t = r['task']; e = es[t['dhatu']['code']]
            issue = entry_scope_issue(e) or oracle_issue(t)
            if not issue and local_issue(t): issue = 'Existing pilot04 local source precaution'
            if not issue and e.code == '10.0023': issue = 'Unresolved urja source alternatives'
            if not issue and t['morphology']['prayoga'] == 'Karmani' and e.artha not in TRANSITIVE_ARTHAS:
                issue = 'Outside existing exact transitive-meaning screen'
            if not issue and t['morphology']['prayoga'] == 'Bhave': issue = 'Outside this diagnostic voice scope'
            if not issue and (r.get('refusals') or r.get('truncated') or not r.get('answer') or r.get('error') or r.get('status') != 'completed'):
                issue = 'Unusable grammatical answer (not a grammatical error label)'
            if issue:
                exclusions[panel][issue] += 1; continue
            if e.code not in bases:
                bases[e.code] = lexical_base(e, vy)
            base = bases[e.code]
            assert base
            is_adanta = name(e.dhatu.gana) == 'Curadi' and e.dhatu.aupadeshika.endswith('a')
            data[fidelity].append(dict(id=t['id'], panel=panel, error=int(not r['is_correct']),
                 family=t['campaign']['root_family'], group=base, code=e.code,
                 gana=name(e.dhatu.gana), lakara=t['morphology']['lakara'], known_adanta=is_adanta,
                 features=features(t, e, base)))
    for fidelity, rows in data.items():
        assert len({r['id'] for r in rows}) == len(rows), fidelity
    assert not ({r['id'] for r in data['xhigh']} & {r['id'] for r in data['high']})
    return data, dict(exclusions), sources


def summarize(rows):
    return dict(n=len(rows), errors=sum(r['error'] for r in rows),
                families=len({r['family'] for r in rows}), groups=len({r['group'] for r in rows}),
                error_families=len({r['family'] for r in rows if r['error']}),
                error_groups=len({r['group'] for r in rows if r['error']}),
                ganas=dict(Counter(r['gana'] for r in rows)),
                error_ganas=dict(Counter(r['gana'] for r in rows if r['error'])))


def weights(rows):
    c = Counter(r['group'] for r in rows)
    return np.array([1 / c[r['group']] for r in rows])


def posterior(err, total):
    return (err + 1.) / (total + 20.)


def fit_rule(rows, mode, top_n=1):
    y = np.array([r['error'] for r in rows], dtype=float)
    w = weights(rows); total = w.sum(); errors = w @ y
    p0 = posterior(errors, total)
    vocab = sorted({f for r in rows for f in r['features'] if mode == 'input_trace' or not f.startswith('trace=')})
    index = {s: i for i, s in enumerate(vocab)}
    x = np.zeros((len(rows), len(vocab)), dtype=float)
    for i, r in enumerate(rows):
        for f in r['features']:
            if f in index: x[i, index[f]] = 1
    count = x.sum(axis=0)
    keep = (count >= 20) & (count <= len(rows) - 20)
    x = x[:, keep]; vocab = [v for v, k in zip(vocab, keep) if k]
    if not vocab: return [dict(rule=[], p_in=p0, p_out=p0, baseline=p0, fallback=True)]
    # Diagonal entries are single features; off-diagonal entries are conjunctions.
    n = x.T @ x
    size = x.T @ (w[:, None] * x)
    err = x.T @ ((w * y)[:, None] * x)
    other_size = total - size; other_err = errors - err
    with np.errstate(divide='ignore', invalid='ignore'):
        pin = np.clip(err / np.maximum(size, 1e-20), 1e-9, 1 - 1e-9)
        pout = np.clip(other_err / np.maximum(other_size, 1e-20), 1e-9, 1 - 1e-9)
        gain = err*np.log(pin) + (size-err)*np.log1p(-pin) + other_err*np.log(pout) + (other_size-other_err)*np.log1p(-pout)
    valid = np.triu(np.ones_like(n, dtype=bool)) & (n >= 20) & (n <= len(rows)-20) & (pin > pout)
    gain[~valid] = -np.inf
    order = np.argsort(-gain.ravel(), kind='stable')
    results = []
    for z in order:
        if not np.isfinite(gain.ravel()[z]): break
        a, b = np.unravel_index(z, gain.shape)
        mask = (x[:, a] > 0) & (x[:, b] > 0)
        inside = [r for r, m in zip(rows, mask) if m]
        outside = [r for r, m in zip(rows, mask) if not m]
        if len({r['group'] for r in inside}) < 8 or len({r['group'] for r in outside}) < 8: continue
        if len({r['group'] for r in inside if r['error']}) < 2: continue
        rules = [vocab[a]] if a == b else [vocab[a], vocab[b]]
        results.append(dict(rule=rules, p_in=posterior(err[a,b],size[a,b]), p_out=posterior(other_err[a,b],other_size[a,b]),
                            baseline=p0, fallback=False, train_inside=summarize(inside),
                            known_adanta_inside=sum(r['known_adanta'] for r in inside),
                            likelihood_objective=float(gain[a,b])))
        if len(results) >= top_n: break
    return results or [dict(rule=[], p_in=p0, p_out=p0, baseline=p0, fallback=True)]


def fit_known(rows):
    w = weights(rows); y = np.array([r['error'] for r in rows]); m = np.array([r['known_adanta'] for r in rows], dtype=bool)
    return dict(rule=['known_adanta'], p_in=posterior(w[m] @ y[m], w[m].sum()),
                p_out=posterior(w[~m] @ y[~m], w[~m].sum()), baseline=posterior(w@y,w.sum()))


def predict(model, r):
    if not model['rule']: return model['baseline']
    match = r['known_adanta'] if model['rule'] == ['known_adanta'] else set(model['rule']) <= set(r['features'])
    return model['p_in'] if match else model['p_out']


def auc(y, p):
    pos = [v for a,v in zip(y,p) if a]; neg = [v for a,v in zip(y,p) if not a]
    if not pos or not neg: return None
    return sum((a > b) + .5*(a == b) for a in pos for b in neg) / (len(pos)*len(neg))


def metrics(rows, preds, selected, seed):
    y = np.array([r['error'] for r in rows]); p = np.clip(np.array(preds), 1e-9, 1-1e-9)
    w = weights(rows); w /= w.sum()
    ss = [r for r,s in zip(rows, selected) if s]
    gs = sorted({r['group'] for r in ss}); n_by=[]; e_by=[]
    for g in gs:
        rr = [r for r in ss if r['group'] == g]; n_by.append(len(rr)); e_by.append(sum(r['error'] for r in rr))
    rng = np.random.default_rng(seed)
    boot=[]
    if gs:
        n_by=np.array(n_by); e_by=np.array(e_by)
        for _ in range(1000):
            ii=rng.integers(len(gs),size=len(gs)); boot.append(1-e_by[ii].sum()/n_by[ii].sum())
    return dict(error_auc=auc(y,p), family_weighted_brier=float(w@((p-y)**2)),
                family_weighted_log_loss=float(w@(-y*np.log(p)-(1-y)*np.log1p(-p))),
                top20=summarize(ss), top20_accuracy=1-sum(r['error'] for r in ss)/len(ss),
                top20_accuracy_family_bootstrap_95=[float(x) for x in np.quantile(boot,[.025,.975])],
                top20_known_adanta=sum(r['known_adanta'] for r in ss),
                mean_predicted_error=float(p.mean()))


def run_cv(primary, historical, scope):
    out=[]; fold_records=[]
    for seed in SEEDS:
        fold=lambda g:hnum(f'{seed}|{g}')%5
        for train_fidelity in ['xhigh', 'high_transfer']:
            training_pool=primary if train_fidelity=='xhigh' else historical
            methods=['intercept','known_adanta','input','input_trace'] if train_fidelity=='xhigh' else ['input','input_trace']
            for method in methods:
                preds={}; selected=set(); records=[]
                for k in range(5):
                    valid=[r for r in primary if fold(r['group'])==k]
                    train=[r for r in training_pool if fold(r['group'])!=k]
                    assert not ({r['group'] for r in train}&{r['group'] for r in valid})
                    assert not ({r['family'] for r in train}&{r['family'] for r in valid})
                    if method=='intercept':
                        w=weights(train); p=posterior(sum(a*r['error'] for a,r in zip(w,train)),w.sum())
                        model=dict(rule=[],baseline=p,p_in=p,p_out=p)
                    elif method=='known_adanta': model=fit_known(train)
                    else: model=fit_rule(train,method)[0]
                    for r in valid: preds[r['id']]=predict(model,r)
                    ranked=sorted(valid,key=lambda r:(-preds[r['id']],hnum(f"{seed}|{r['id']}")))
                    selected.update(r['id'] for r in ranked[:math.ceil(.2*len(ranked))])
                    records.append(dict(fold=k,train=summarize(train),validation=summarize(valid),model=model,family_overlap=0,broad_group_overlap=0))
                result=dict(scope=scope,seed=seed,training_fidelity=train_fidelity,method=method,
                            **metrics(primary,[preds[r['id']] for r in primary],[r['id'] in selected for r in primary],seed))
                out.append(result)
                fold_records.append(dict(scope=scope,seed=seed,training_fidelity=train_fidelity,method=method,folds=records))
                print(scope,seed,train_fidelity,method,'top20',result['top20']['n']-result['top20']['errors'],'/',result['top20']['n'],'AUC',result['error_auc'],flush=True)
            status('Family-disjoint surrogate validation',f'{scope}: completed seed {seed}, training fidelity {train_fidelity}. All validation root groups remain absent from fitting and rule selection.')
    return out,fold_records


def main():
    target=OUT/'surrogate-04.results.json'
    if target.exists(): raise SystemExit('Preserve completed diagnostic; use a versioned revision.')
    status('Assembling development-only surrogate data','Applying policy14 and existing source precautions; preparing phonology, citation, coordinate and trace predictors without answer-form features.')
    data,exclusions,sources=load_data()
    datasets={fidelity:{'all':summarize(rows),'without_known_adanta':summarize([r for r in rows if not r['known_adanta']])} for fidelity,rows in data.items()}
    write(OUT/'surrogate-04.dataset.json',dict(created_at=now(),policy='oracle-policy-14.json',datasets=datasets,exclusions=exclusions,sources=sources,development_only=True))
    write(OUT/'surrogate-04.development-features.json',data)
    print('DATA',json.dumps(datasets),flush=True)
    status('Development signal inventory',f"Current xHigh source-screened sample has {datasets['xhigh']['all']['n']} completed questions and {datasets['xhigh']['all']['errors']} errors. Outside known adanta: {datasets['xhigh']['without_known_adanta']['errors']} errors in {datasets['xhigh']['without_known_adanta']['error_groups']} broad root groups.")
    results=[];folds=[]
    for scope in ['all','without_known_adanta']:
        keep=lambda r:scope=='all' or not r['known_adanta']
        primary=[r for r in data['xhigh'] if keep(r)];historical=[r for r in data['high'] if keep(r)]
        rr,ff=run_cv(primary,historical,scope);results+=rr;folds+=ff
    full_rules={scope:{mode:fit_rule([r for r in data['xhigh'] if scope=='all' or not r['known_adanta']],mode,10) for mode in ['input','input_trace']} for scope in ['all','without_known_adanta']}
    write(OUT/'surrogate-04.fold-audit.json',dict(created_at=now(),fold_seeds=SEEDS,fold_rule='sha256(seed|initial_lexical_base) modulo5; all ganas and citation-marker variants sharing a base stay together',evaluations=folds,no_master_test_answers=True))
    write(target,dict(created_at=now(),run_id=RUN_ID,policy='oracle-policy-14.json',design_sha256=sha(OUT/'surrogate-04.design.json'),generator_sha256=sha(__file__),dataset_sha256=sha(OUT/'surrogate-04.dataset.json'),datasets=datasets,metrics=results,full_training_rules_exploratory_only=full_rules,limits=['Retrospective family cross-validation does not erase adaptive pilot selection or prior human access; it is not a fresh release evaluation.','Historical High/4096 transfer is explicitly separated from xHigh/16384 fitting and cannot supply a strongest-reference accuracy claim.','Small event and family counts, repeated hypotheses and covariate selection limit inference; bootstrap intervals are conditional diagnostics, not selection-corrected guarantees.','Passing existing scope gates is not complete independent source certification.'],no_master_test_answers=True,worker_paid_calls=0,benchmark_ready=False))
    print('DONE',target,flush=True)


if __name__=='__main__':main()
