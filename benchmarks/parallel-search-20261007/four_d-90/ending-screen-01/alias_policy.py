"""Finite, task-bound spelling whitelist; no universal gemination normalizer.

The builder reads only the 96 canonical keys. Grading uses the saved whitelist,
not the builder, and never rewrites a response or canonical gold.
"""
import hashlib
import itertools
import json
from pathlib import Path
from finetune.prompts import extract_answer, slp1_to_devanagari
from misc.oai_batch_eval import normalize

OUT=Path(__file__).resolve().parent
VOWELS=set('aAiIuUfFxXeEoO')
CONS=set('kKgGNcCjJYwWqQRtTdDnpPbBmyrlvSzsh')
YAR=CONS-{'h'}
DEASP=dict(zip('KGCJWQTDPB','kgcjwqtdpb'))
URL=lambda r:f'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/{r[0]}/{r}.htm'

def sites(form):
    """Original positions only: no recursive applications, no arbitrary collapse."""
    positions={};unresolved=[]
    def add(i,rule,condition):
        first=DEASP.get(form[i],form[i])
        positions[i]=dict(index=i,original=form[i],replacement=first+form[i],
                          rule=rule,condition=condition)
    if form[-1] in 'ntd':
        add(len(form)-1,'8.4.47','Word-final yar at pause; n stays dental, t/d branch retained.')
    for i,c in enumerate(form):
        if (i>=2 and form[i-2] in VOWELS and form[i-1] in 'rh'
                and c in YAR-{'r'}):
            if c in 'Szs' and i+1<len(form) and form[i+1] in VOWELS:
                continue  # 8.4.49: no sar doubling before a vowel.
            add(i,'8.4.46','Postvocalic r/h followed by yar; exclude r/h target and sar before vowel.')
        if (i and i+1<len(form) and form[i-1] in VOWELS
                and c in YAR-{'r'} and form[i+1] in CONS):
            j=i
            while j<len(form) and form[j] in CONS:j+=1
            run=form[i:j]
            if len(run)!=2 or DEASP.get(run[0],run[0])==DEASP.get(run[1],run[1]):
                unresolved.append(dict(index=i,cluster=run,
                    reason='Existing gemination/cC or at least three consonants: broader closure not certified.'))
                continue
            add(i,'8.4.47','Postvocalic yar before a consonant, original two-distinct-consonant run; r/h target excluded.')
    return sorted(positions.values(),key=lambda x:x['index']),unresolved

def build(tasks):
    items=[]
    for t in tasks:
        proofs={};unresolved=[]
        for f in t['gold_slp1']:
            ss,uu=sites(f)
            unresolved.extend(dict(canonical_slp1=f,**u) for u in uu)
            for bits in itertools.product([False,True],repeat=len(ss)):
                chosen=[s for s,on in zip(ss,bits) if on]
                if not chosen:continue
                changes={s['index']:s['replacement'] for s in chosen}
                alias=''.join(changes.get(i,c) for i,c in enumerate(f))
                if alias in t['gold_slp1']:continue
                proofs.setdefault(alias,[]).append(dict(canonical_slp1=f,
                    applications=chosen,combination='Each independently licensed original position applied once.'))
        aliases=sorted(proofs)
        items.append(dict(task_id=t['id'],canonical_forms_devanagari=t['gold_devanagari'],
            canonical_forms_slp1=t['gold_slp1'],aliases_devanagari=list(map(slp1_to_devanagari,aliases)),
            aliases_slp1=aliases,evidence=[dict(alias_slp1=a,derivations=proofs[a]) for a in aliases],
            unresolved_contexts=unresolved))
    return dict(schema_version=1,kind='Fixed96 pre-outcome task-specific spelling whitelist',
        task_count=96,primary_score='canonical_or_listed_alias',secondary_score='canonical_only',
        canonical_tasks_sha256=hashlib.sha256((OUT/'proposedtasks.json').read_bytes()).hexdigest(),
        sources=[URL(r) for r in ['8.4.46','8.4.47','8.4.49','8.4.50','8.4.51','8.4.53','8.4.55','8.4.56']],
        scope='Optional final n/t/d doubling; postvocalic r/h-conditioned doubling; simple postvocalic two-consonant clusters. Deaspirate first copied aspirated stop by jhalam jas jhasi or khari ca, preserving the voicing class. Finite whitelist only.',
        limits='Not exhaustive classical spelling certification. Existing gemination/cC and >=3-consonant closure is not generated. All usable unrecognized responses require source review before wrong-family counts or advancement; report later adjudication separately and symmetrically.',
        model_inputs_unchanged=True,canonical_gold_unchanged=True,items=items)

def validate_policy(policy,tasks):
    if len(tasks)!=96 or len(policy['items'])!=96:
        raise ValueError('Requires exact96 policy and questions')
    if [x['task_id'] for x in policy['items']] != [t['id'] for t in tasks]:
        raise ValueError('Policy question membership/order mismatch')
    for item,t in zip(policy['items'],tasks):
        if item['canonical_forms_devanagari']!=t['gold_devanagari'] or item['canonical_forms_slp1']!=t['gold_slp1']:
            raise ValueError('Canonical key changed')
        if item['aliases_devanagari']!=list(map(slp1_to_devanagari,item['aliases_slp1'])):
            raise ValueError('Alias transliteration changed')
        if len(set(item['aliases_devanagari']))!=len(item['aliases_devanagari']):
            raise ValueError('Duplicate alias')
    return {x['task_id']:x for x in policy['items']}

def grade_policy(output_text,task_id,policy):
    """Same benchmark extraction/NFC rule; no status/completion inference here."""
    matched=[x for x in policy['items'] if x['task_id']==task_id]
    if len(matched)!=1:raise ValueError('Unknown or duplicate task policy')
    item=matched[0];answer=extract_answer(output_text)
    canonical={normalize(g) for g in item['canonical_forms_devanagari']}
    aliases={normalize(g) for g in item['aliases_devanagari']}
    n=normalize(answer) if answer is not None else None
    return dict(answer=answer,canonical_correct=n in canonical,
        alias_aware_correct=n in canonical|aliases,
        requires_source_adjudication=answer is not None and n not in canonical|aliases)

if __name__=='__main__':
    tasks=json.loads((OUT/'proposedtasks.json').read_text())
    policy=build(tasks);validate_policy(policy,tasks)
    (OUT/'alias-policy.json').write_text(json.dumps(policy,ensure_ascii=False,indent=2)+'\n')
    print(dict(tasks=len(tasks),alias_tasks=sum(bool(x['aliases_slp1']) for x in policy['items']),
        aliases=sum(len(x['aliases_slp1']) for x in policy['items']),
        unresolved_context_tasks=sum(bool(x['unresolved_contexts']) for x in policy['items'])))
