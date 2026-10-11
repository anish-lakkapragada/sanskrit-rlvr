"""Full-panel input/receipt/grading review; refuses partial Astra panels."""
from pathlib import Path
import collections,copy,datetime,hashlib,importlib.util,json,math,re,sys,unicodedata
import numpy as np
ROOT=Path.cwd();sys.path.insert(0,str(ROOT));OUT=ROOT/'benchmarks/parallel-search-20261007/astra-comparison-01';JOBS=ROOT/'benchmarks/iterative-goal-20261006/jobs';BASE=OUT.parent/'four_d-90'
from misc.vp_4d_pilot import load_entries
from misc.vp_cartesian_task import make_task,validate_task
from misc.vp_cartesian_prompt_v1 import render
from vidyut.lipi import transliterate,Scheme

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def norm(s):return unicodedata.normalize('NFC',s.strip())
ledger=read(JOBS.parent/'ledger.json');anames=[f'astra-simple4d-direct-{i:02d}' for i in range(1,21)];onames=[f'opus-fast-simple4d-{i:02d}' for i in range(1,6)]
assert all(ledger['jobs'][n].get('settled') and ledger['jobs'][n].get('collected_at') for n in anames),'No interim review permitted'
gate={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'settled_and_collected_jobs':20,'receipts':sum(len(list((JOBS/n).glob('task-*.result.json'))) for n in anames),'first_observed_complete_at':'2026-10-08T00:08:48.675797+00:00','interim_answers_or_scores_read':False}
plan=read(OUT/'plan.json');sources=[];panels={};request_checks=[];response_ids=set()
for provider,names in [('Astra',anames),('Opus',onames)]:
 rows_all=[]
 for name in names:
  p=JOBS/name;j=ledger['jobs'][name];assert j.get('settled') and j.get('collected_at')
  tasks=read(p/'tasks.json');reqs=read(p/'requests.json');rows=read(p/'results.json');assert len(tasks)==len(reqs)==len(rows)==(10 if provider=='Astra' else 40)
  sources.append({'job':name,**{f:sha(p/f) for f in ['tasks.json','requests.json','results.json']}})
  for t,req,row in zip(tasks,reqs,rows):
   assert row['task']==t and row['request']==req and row['task_id']==t['id'] and row['custom_id']==req['custom_id']
   assert row['attempt_number']==1 and row['sample_index']==0 and row['transport']=='direct'
   raw=row['raw_batch_result'];assert raw['custom_id']==req['custom_id'];prompt=render(t)
   if provider=='Astra':
    b=req['body'];assert b['model']=='gpt-6-astra' and b['reasoning']=={'mode':'standard','effort':'xhigh'} and b['max_output_tokens']==65536
    assert b['input']==[{'role':'user','content':prompt}] and b['tools']==[] and b['tool_choice']=='none' and b['truncation']=='disabled' and b['stream'] is False
    eff=read(p/(req['custom_id']+'.effective-request.json'));assert eff['body']==dict(b,service_tier='default')
    # Match the frozen runner's canonical JSON hash convention independently.
    plain=digest
    assert eff['canonical_request_digest']==plain(req) and eff['effective_body_digest']==plain(eff['body'])
    assert read(p/(req['custom_id']+'.result.json'))==raw
    body=raw['response']['body'];assert raw['response']['status_code']==200 and body['status']=='completed' and not body.get('error') and body['model']=='gpt-6-astra' and body['service_tier']=='default'
    assert body['id'] not in response_ids;response_ids.add(body['id']);u=body['usage']
    assert type(u['input_tokens']) is int and 0<=u['input_tokens']<=1500 and type(u['output_tokens']) is int and 0<=u['output_tokens']<=65536
    assert u['total_tokens']==u['input_tokens']+u['output_tokens'];assert not (body.get('incomplete_details') or {})
    contents=[c for x in body['output'] if x['type']=='message' for c in x['content']]
    text=''.join(c.get('text','') for c in contents if c['type']=='output_text');assert not any(c['type']=='refusal' for c in contents)
   else:
    b=req['params'];assert b['model']=='claude-opus-5-5' and b['max_tokens']==65536 and b['output_config']['effort']=='xhigh'
    assert b['messages']==[{'role':'user','content':prompt}] and b['tools']==[] and b['tool_choice']=={'type':'none'}
    body=raw['result']['message'];assert raw['result']['type']=='succeeded';assert body['stop_reason']=='end_turn'
    text=''.join(c['text'] for c in body['content'] if c['type']=='text')
   assert text==row['output_text']
   matches=re.findall(r'<answer>(.*?)</answer>',text,re.S);assert len(matches)==1 and matches[0].strip()
   answer=matches[0].strip();correct=norm(answer) in {norm(g) for g in t['gold_devanagari']}
   assert answer==row['answer'] and norm(answer)==row['answer_normalized'] and correct==row['is_correct']
   assert row['status']=='completed' and not row['truncated'] and not row['refusals'] and not row['error']
   request_checks.append({'provider':provider,'job':name,'task_id':t['id'],'request_verified':True,'raw_text_and_canonical_grade_reproduced':True})
  rows_all.extend(rows)
 panels[provider]=rows_all
astra=panels['Astra'];opus=panels['Opus'];tasks=[r['task'] for r in astra]
assert len(astra)==len(opus)==200 and [r['task'] for r in opus]==tasks==read(JOBS/'opus-simple4d-90-01/tasks.json')
assert len({t['id'] for t in tasks})==200
entries={e.code:e for e in load_entries()}
for t in tasks:
 validate_task(t,entries[t['dhatu']['code']],'development')
 e=make_task(entries[t['dhatu']['code']],'development',t['morphology']);assert e['gold_slp1']==t['gold_slp1'] and e['gold_devanagari']==t['gold_devanagari']
oldreview=read(BASE/'direct-result-source-review.json');oldmiss={d['id'] if 'id' in d else d['task_id']:d for d in oldreview['disagreements']}
# This is a symmetric post-result sensitivity check, not a retroactive frozen score.
s=importlib.util.spec_from_file_location('existing_finite_alias_rules',BASE/'ending-screen-01/alias_policy.py');ar=importlib.util.module_from_spec(s);s.loader.exec_module(ar);aliases={i['task_id']:i for i in ar.build(tasks)['items']}
alias_rescues={};
for provider,rows in panels.items():
 alias_rescues[provider]=[r['task_id'] for r in rows if not r['is_correct'] and norm(r['answer']) in {norm(x) for x in aliases[r['task_id']]['aliases_devanagari']}]
assert not any(alias_rescues.values())
SK='https://jainqq.org/explore/002377/241';WS='https://sa.wikisource.org/wiki/सिद्धान्तकौमुदी/प्रकरण‌५१-६०'
R=lambda s:f'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/{s[0]}/{s}.htm'
mis=[];successes=[r for r in astra if r['is_correct']]
for a,o in zip(astra,opus):
 if a['is_correct']:continue
 t=a['task'];code=t['dhatu']['code'];answer=transliterate(a['answer'],Scheme.Devanagari,Scheme.Slp1)
 if code=='10.0441':
  category='agarviya_ending_set_with_or_without_stem_error';explanation='The exact गृह ग्रहणे entry lies in the explicitly Atmanepada agārviya section, which prints गृहयते. The answer selects a Parasmaipada ending; forms with गर्ह additionally strengthen the wrong stem vowel.';evidence=[SK,R('6.4.48')];strength='Direct lexical stem and ending-set evidence; requested finite form inferred by rules.'
 elif code in {'10.0444','10.0448'}:
  category='agarviya_ending_set';explanation='शूर and सत्र lie inside the explicit agārviya Atmanepada section. The submitted Parasmaipada ending is not an unselected alternative; the intrinsic lexical restriction supplies the ending set.';evidence=[SK];strength='Direct lexical ending-set evidence; exact person-number extension is rule inference.'
 elif code=='10.0408':
  category='wrong_krpa_stem';explanation='For कृप दौर्बल्ये the printed lexical source explicitly gives कृपयति. कर्पय- strengthens the stem incorrectly; कल्पय- substitutes another lexical stem.';evidence=[SK,R('6.4.48')];strength='Direct lexical stem evidence; finite extension by rules.'
 elif code in {'10.0419','10.0428','10.0426'}:
  category='adanta_aorist_vowel_quantities';explanation='The literal-a adanta readings शील, भाज and वास preserve the long root vowel in this reduplicated aorist while their reduplicative vowel is short. The submitted form reverses those quantities; intrinsic final-a deletion affects the usual shortening/lengthening conditions.';evidence=[SK,R('6.4.48'),R('7.4.2'),R('7.4.93')];strength='Direct lexical identity plus rule inference; not an independently printed full paradigm.'
 elif code=='06.0067':
  category='kur_required_lengthening';explanation='Same response and exact task as the prior Opus source review. Tudadi कुर् शब्दे requires the long vowel of कूर्यास्व; the कृ-derived exception does not establish कुर्यास्व for this lexical root.';evidence=[R('8.2.77'),R('8.2.79'),'https://jainqq.org/explore/004319/118'];strength='Previously checked primary lexical distinction and general lengthening rule.'
 elif code=='06.0085':
  category='vil_missing_guna';explanation='The हलन्त root विल् has a light i penultimate vowel. Before the eligible periphrastic-future suffix,7.3.86 yields vel-, hence वेलितास्थः. The unchanged vil- response omits guṇa; no Kutadi classification is supplied for this earlier root.';evidence=[R('7.3.86'),R('1.2.1')];strength='Rule inference for the exact dictionary entry; no extra spelling branch demonstrated.'
 elif code=='04.0100':
  category='dam_wrong_aorist_formation';explanation='The Divadi पुषादि section takes अङ् in Parasmaipada aorists under3.1.55. Dhatupradipa scan108 explicitly gives दाम्यति and अदमत् for दमु उपशमे. Extending the अङ् form to third-person plural gives अदमन्, not the submitted iṣ-aorist.';evidence=[R('3.1.55'),'https://jainqq.org/explore/004319/108'];strength='Direct representative aorist plus rule-based third-plural extension.'
 elif code=='06.0097':
  category='gud_kutadi_guna_block';explanation='गुड् रक्षायाम् belongs to the Tudadi Kutadi span. Its non-ñit/ṇit suffix behaves as ṅit under1.2.1, blocking guṇa by1.1.5. The response wrongly changes guḍ- to goḍ-. Dhatupradipa scan121 supplies the same unstrengthened lexical stem.';evidence=[R('1.2.1'),R('1.1.5'),'https://jainqq.org/explore/004319/121'];strength='Primary lexical context plus generic rule inference.'
 elif code=='04.0032':
  category='mi_middle_optative_dual_ending';explanation='मीङ् is intrinsically Atmanepada (1.3.12), with the Divadi ya theme (3.1.69). The middle optative dual contains sīyuṭ and Ātām; after s-deletion and vowel combination this yields मीयेयाताम्. मीयेताम् loses the required middle optative dual sequence.3.4.102 explicitly illustrates पचेयाताम्/एधेयाताम्.';evidence=[R('1.3.12'),R('3.1.69'),R('3.4.102'),R('7.2.79'),R('6.1.87')];strength='Explicit parallel ending examples plus root-specific rule inference.'
 else:
  assert t['campaign']['sampling_cell']['label']=='short_adanta_non_aorist',code
  category='adanta_stem_strengthening';explanation='The supplied literal-final-a Curadi entry belongs to the adanta group. The submitted vowel strengthening is absent from its prescribed short stem: deleting the final lexical a does not license ordinary consonant-root strengthening. The lexical source and6.4.48 support the unstrengthened form.';evidence=[WS,SK,R('6.4.48')];strength='Primary lexical classification/stem evidence plus rule inference across the requested tense.'
 pool=[r for r in successes if r['task']['campaign']['root_family']==t['campaign']['root_family']] or [r for r in successes if r['task']['dhatu']['gana']==t['dhatu']['gana'] and r['task']['campaign']['sampling_cell']['label']==t['campaign']['sampling_cell']['label']] or successes
 match=min(pool,key=lambda r:r['task_id'])
 mis.append({'id':t['id'],'dhatu':t['dhatu'],'morphology':t['morphology'],'cell':t['campaign']['sampling_cell']['label'],'astra_answer':a['answer'],'astra_answer_slp1':answer,'gold_slp1':t['gold_slp1'],'gold_devanagari':t['gold_devanagari'],'category':category,'assessment':explanation,'evidence':evidence,'evidence_strength':strength,'concrete_key_or_scoring_defect_identified':False,'licensed_submitted_variant_identified':False,'opus_correct':o['is_correct'],'opus_answer':o['answer'],'existing_opus_miss_review':t['id'] in oldmiss,'matched_success_id':match['task_id'],'matched_success_answer':match['answer']})
assert len(mis)==39
cells={provider:{cell:{'correct':sum(r['is_correct'] for r in rows if r['task']['campaign']['sampling_cell']['label']==cell),'n':sum(r['task']['campaign']['sampling_cell']['label']==cell for r in rows)} for cell in sorted({t['campaign']['sampling_cell']['label'] for t in tasks})} for provider,rows in panels.items()}
transitions=collections.Counter(f"opus_{int(o['is_correct'])}_astra_{int(a['is_correct'])}" for a,o in zip(astra,opus))
fam=collections.defaultdict(lambda:np.zeros(3))
for a,o in zip(astra,opus):fam[a['task']['campaign']['root_family']]+=(1,int(a['is_correct']),int(o['is_correct']))
vals=np.array([fam[k] for k in sorted(fam)]);rng=np.random.default_rng(20261008);est=[]
for i in range(0,20000,250):
 draw=vals[rng.integers(0,len(vals),size=(250,len(vals)))].sum(axis=1);est.extend(((draw[:,1]-draw[:,2])/draw[:,0]).tolist())
paired={'n':200,'families':len(fam),'direction':'Astra minus Opus','accuracy_difference_pp':-7.0,'transitions':dict(transitions),'family_bootstrap_95_interval_pp':(100*np.quantile(est,[.025,.975])).tolist(),'bootstrap_repetitions':20000,'bootstrap_seed':20261008,'exact_discordant_pair_binomial_two_sided_p':min(1,2*sum(math.comb(48,k) for k in range(18))/2**48),'limitation':'Adaptive development cohort; models are paired, families dependent; does not qualify a held-out benchmark or sub1pp precision.'}
summary={provider:{'n':200,'correct':sum(r['is_correct'] for r in rows),'accuracy':sum(r['is_correct'] for r in rows)/200,'usable':200,'refusals':0,'truncations':0,'unparsed':0,'errors':sum(not r['is_correct'] for r in rows),'wrong_families':len({r['task']['campaign']['root_family'] for r in rows if not r['is_correct']}),'wrong_lun':sum(not r['is_correct'] and r['task']['morphology']['lakara']=='Lun' for r in rows),'wrong_non_lun':sum(not r['is_correct'] and r['task']['morphology']['lakara']!='Lun' for r in rows)} for provider,rows in panels.items()}
result={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'full_panel_gate':gate,'mechanical_protocol_and_grading_review_passed':True,'n':200,'tasks_sha256':sha(BASE/'tasks.json'),'paired_identical_complete_tasks':True,'all200_gold_unions_regenerated':True,'request_and_raw_grading_checks':request_checks,'raw_summary':summary,'cells':cells,'paired':paired,'astra_miss_reviews':mis,'astra_errors_by_category':dict(collections.Counter(d['category'] for d in mis)),'symmetric_existing_alias_sensitivity':{'classification':'Post-result sensitivity audit; does not overwrite raw/frozen canonical score.','helper_sha256':sha(BASE/'ending-screen-01/alias_policy.py'),'rescued_ids':alias_rescues,'canonical_scores_unchanged':True},'prior_opus_all25_review':{'path':str((BASE/'direct-result-source-review.json').relative_to(ROOT)),'sha256':sha(BASE/'direct-result-source-review.json'),'all_prior_result_hashes_unchanged':all(sha(ROOT/x['path'])==x['sha256'] for x in oldreview['sources'])},'source_snapshots':read(OUT/'independent-source-cache/index.json'),'other_source_inputs':oldreview['source_inputs'],'sources':sources,'score_corrections_requested':[],'new_source_holds_requested':[],'full_independent_paradigm_or_spelling_certification':False,'raw_results_changed':False,'provider_calls':0,'ledger_or_job_edits':False,'benchmark_ready':False,'limitations':['All39 Astra misses assessed; no concrete licensed submitted variant or invalid key demonstrated. Source evidence is often lexical/representative plus grammatical inference, not all-person paradigm attestation.','Neither200-question development panel is a final held-out benchmark. Model ranking and grammar mixture were investigated adaptively.','Observed performance does not establish an iid or family-generalization standard error below1percentage point.','Finite spelling sensitivity check is not exhaustive; any later supported source correction must apply symmetrically.']}
assert result['prior_opus_all25_review']['all_prior_result_hashes_unchanged']
(OUT/'independent-result-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'summary':summary,'cells':cells,'paired':paired,'categories':result['astra_errors_by_category'],'alias_rescues':alias_rescues},ensure_ascii=False,indent=2));print('review_sha256',sha(OUT/'independent-result-review.json'))
