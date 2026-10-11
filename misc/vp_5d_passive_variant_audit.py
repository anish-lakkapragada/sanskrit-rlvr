"""Independent source controls and prospective supply exclusion for Cinvat."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from misc import vp_campaign_candidates as old
from misc.vp_5d_pilot import OUT,RECIPES,atomic_json,now,sha
from misc.vp_5d_release_feasibility import PN,cell,status
from vidyut.prakriya import Vyakarana,Pada,Sanadi,Lakara,Prayoga,Purusha,Vacana

SOURCE62='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.62.htm'
SOURCE93='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.93.htm'


def derive(v,e,ops,la,pu='Prathama',va='Eka'):
    return v.derive(Pada.Tinanta(dhatu=e.dhatu.with_sanadi([getattr(Sanadi,s) for s in ops]),
        lakara=getattr(Lakara,la),prayoga=Prayoga.Karmani,purusha=getattr(Purusha,pu),vacana=getattr(Vacana,va)))


def main():
    es={e.code:e for e in old.load_entries()};families={};v=Vyakarana()
    for e in old.load_entries():families.setdefault(old.family(e),e)
    definitions=[
        (['Ric'],'Lut',['SamitA','SAmitA','SamayitA'],SOURCE62,'Direct traditional causative passive periphrastic-future examples.'),
        (['Ric'],'Lrt',['Samizyate','SAmizyate','Samayizyate'],SOURCE62,'Direct traditional causative passive future examples.'),
        (['Ric'],'Lun',['aSami','aSAmi'],SOURCE93,'Direct literal-cin passive aorist control.'),
        (['yaN','Ric'],'Lut',['SaMSamitA','SaMSAmitA','SaMSamayitA'],SOURCE93,'Direct Balamanorama intensive-causative passive periphrastic-future examples.'),
        (['yaN','Ric'],'Lun',['aSaMSami','aSaMSAmi'],SOURCE93,'Direct Kashika intensive-causative passive aorist examples.'),
    ]
    checks=[]
    for ops,la,expected,source,note in definitions:
        ps=derive(v,es['04.0098'],ops,la);gold=sorted({p.text for p in ps})
        checks.append({'dhatu_code':'04.0098','sanadi':ops,'lakara':la,'prayoga':'Karmani',
            'purusha':'Prathama','vacana':'Eka','direct_source_forms_slp1':expected,'vp_forms_slp1':gold,
            'missing_source_forms':sorted(set(expected)-set(gold)),'source':source,'evidence_level':'direct_example',
            'note':note,'trace_rules':sorted({h.code for p in ps for h in p.history if h.code in {'6.4.62','6.4.92','6.4.93'}})})
    pilot=json.loads((OUT/'pilot-01.tasks.json').read_text())
    def modifier_row(e):
        return {'code':e.code,'family':old.family(e),'citation':e.dhatu.aupadeshika,
            'prefixes':list(e.dhatu.prefixes),'sanadi':[old.name(s) for s in e.dhatu.sanadi]}
    hidden=[modifier_row(e) for e in es.values() if e.dhatu.prefixes or e.dhatu.sanadi]
    pilot_hidden=[modifier_row(es[t['dhatu']['code']]) for t in pilot
        if es[t['dhatu']['code']].dhatu.prefixes or es[t['dhatu']['code']].dhatu.sanadi]
    modifier_audit={'created_at':now(),'pilot_count_checked':len(pilot),'pilot_affected':pilot_hidden,
        'all_dictionary_entries_with_hidden_modifiers':hidden,'no_pilot_changes':True,
        'scope':'Actual Dhatu fields before applying any requested sanadi recipe.',
        'dictionary_sha256':sha(old.TSV),'pilot_sha256':sha(OUT/'pilot-01.tasks.json')}
    atomic_json(OUT/'pilot-01.hidden-modifier-audit.json',modifier_audit)
    affected=[{'task_id':t['id'],'dhatu_code':t['dhatu']['code'],'recipe':t['derivation']['recipe_id'],
        'morphology':t['morphology']} for t in pilot if t['morphology']['prayoga']=='Karmani'
        and t['morphology']['lakara'] in {'Lut','Lrt'} and {'6.4.62','6.4.92'}<=set(t['campaign']['trace_rule_ids'])]
    audit={'created_at':now(),'issue':'Optional lengthening under 6.4.93 in Cinvat passive futures',
        'vp_version':'0.4.0','source_checks':checks,'affected_pilot_contexts':affected,
        'code_evidence':'Current separately cloned upstream asiddhavat.rs lines 859–877 limits is_cin_namuloh to literal ciR/Ramul, while the later nic-deletion branch recognizes Cinvat. Source inspection is explanatory evidence; the installed 0.4.0 reproductions are recorded above.',
        'interpretation':'Strong evidence of missing permitted long-vowel variants. The source directly discusses the ordinary causal forms and the intensive-causal periphrastic future. Some commentary traditions differ about nested lengthening, reinforcing the need to accept the documented alternatives or conservatively exclude the context.',
        'prospective_exclusion':{'prayoga':'Karmani','lakaras':['Lut','Lrt'],'require_rules_all':['6.4.62','6.4.92']},
        'pilot_policy':'Preserve all raw gold, responses and scores. The nam pilot answer lengthens while retaining the causal aya; the source-supported long branch deletes nic, so this is not a demonstrated correction to that model answer.',
        'gold_repaired':False,'script_sha256':sha(Path(__file__))}
    atomic_json(OUT/'release-feasibility-01.passive-oracle-review.json',audit)
    path=OUT/'release-feasibility-01.supply.json';data=json.loads(path.read_text())
    removed=Counter();affected_families=set();hidden_removed=Counter();hidden_families=[]
    for row in data['rows']:
        e=families[row['family']]
        if e.dhatu.prefixes or e.dhatu.sanadi:
            hidden_families.append(modifier_row(e))
            for key,mask in row['eligible_person_number_masks'].items():
                hidden_removed[key]+=mask.bit_count()
            row['eligible_person_number_masks']={}
            continue
        for key,mask in list(row['eligible_person_number_masks'].items()):
            recipe,la,voice=key.split('|')
            if voice!='Karmani' or la not in {'Lut','Lrt'}:continue
            newmask=mask
            for bit,(pu,va) in enumerate(PN):
                if not mask&(1<<bit):continue
                ps=derive(v,e,RECIPES[recipe]['sanadi'],la,pu,va)
                rules={h.code for p in ps for h in p.history if old.name(h.source)=='Ashtadhyayi'}
                if {'6.4.62','6.4.92'}<=rules:
                    newmask &= ~(1<<bit);removed[key]+=1;affected_families.add(row['family'])
            if newmask:row['eligible_person_number_masks'][key]=newmask
            else:del row['eligible_person_number_masks'][key]
    data['created_at']=now();data['source_census_sha256']=sha(path)
    data['accepted_tuples']-=sum(removed.values())+sum(hidden_removed.values())
    data['prospective_rule_exclusion']=audit['prospective_exclusion'];data['removed_tuples']=sum(removed.values())
    data['removed_by_cell']=dict(removed);data['affected_family_count']=len(affected_families)
    data['hidden_modifier_exclusion']={'condition':'Actual Dhatu.prefixes or Dhatu.sanadi nonempty before requested recipe',
        'families':hidden_families,'removed_tuples':sum(hidden_removed.values()),'removed_by_cell':dict(hidden_removed)}
    data['eligible_master_test_families']=sum(bool(r['eligible_person_number_masks']) for r in data['rows'])
    data['eligible_family_gana']=dict(Counter(r['gana'] for r in data['rows'] if r['eligible_person_number_masks']))
    data['total_removed_tuples']=sum(removed.values())+sum(hidden_removed.values())
    data['variant_count_histogram_note']='Original-census histogram; not recomputed after prospective exclusion.'
    data['no_final_membership']=True;data['review_script_sha256']=sha(Path(__file__))
    atomic_json(OUT/'release-feasibility-01.reviewed-supply.json',data)
    print(json.dumps({'direct_examples_missing':[x['missing_source_forms'] for x in checks],
        'pilot_contexts':affected,'removed_tuples':sum(removed.values()),'remaining_tuples':data['accepted_tuples'],
        'affected_families':len(affected_families),'hidden_modifier_removed_tuples':sum(hidden_removed.values()),
        'hidden_modifier_families':hidden_families,'pilot_hidden_modifiers':pilot_hidden},indent=2))


if __name__=='__main__':main()
