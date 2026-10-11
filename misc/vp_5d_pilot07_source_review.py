"""Bounded pilot07 input/oracle source controls; no model outcomes."""
import json
from pathlib import Path
from collections import Counter
import requests
from misc.vp_5d_prepare_04 import OUT, ROOT, atomic_json, now, sha
from misc.vp_5d_candidate_nested_audit import traces, TextParser

B = OUT / 'pilot-07'

def main():
    tasks = json.loads((B / 'tasks.json').read_text())
    candidate = json.loads((OUT / 'candidate-4800/revision-03/tasks.json').read_text())
    sources = []
    for rule in ['2.4.47','7.2.58','3.1.29','3.1.31','3.1.7','3.4.114','6.4.78','7.4.80','7.4.87','7.4.88']:
        url = f'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/{rule[0]}/{rule}.htm'
        response = requests.get(url, timeout=25)
        if response.status_code != 200:
            sources.append(dict(rule=rule,url=url,http_status=response.status_code,review_source='Primary text read with browser; local HTTP cache unavailable.'))
            continue
        response.encoding = 'utf-8'
        path = B / 'source-controls' / (rule + '.html'); path.parent.mkdir(exist_ok=True)
        path.write_text(response.text)
        parser = TextParser(); parser.feed(response.text)
        txt = path.with_suffix('.txt'); txt.write_text(' '.join(x.strip() for x in parser.parts if x.strip()))
        sources.append(dict(rule=rule, url=url, html_sha256=sha(path), text_sha256=sha(txt)))
    controls = []
    for code, ops in [('01.1166',[]),('01.1166',['san']),('02.0040',['san']),('10.0277',['san']),('10.0235',['san']),('01.0608',['yaNluk','Ric'])]:
        for lakara in ['Lat','Lut','Lun']:
            morphology=dict(lakara=lakara,prayoga='Kartari',purusha='Prathama',vacana='Eka')
            controls.append(dict(code=code,operations=ops,morphology=morphology,derivations=traces(code,ops,morphology)))
    suspect = [t for t in tasks if t['dhatu']['code']=='01.1166' and t['derivation']['sanadi']==['san']]
    history = json.loads((B/'exposure-and-novelty-audit.json').read_text())['historical_input_snapshot']['task_files']
    old = []
    for file in history:
        for t in json.loads(Path(file['path']).read_text()):
            if t.get('dhatu',{}).get('code')=='01.1166':
                old.append(dict(source=file['path'],id=t.get('id'),operations=t.get('derivation',{}).get('sanadi'),morphology=t.get('morphology')))
    report = dict(created_at=now(), task_sha256=sha(B/'tasks.json'), candidate_sha256=sha(OUT/'candidate-4800/revision-03/tasks.json'),
      sources=sources, controls=controls, read_model_answers=False,
      dispositions=[
        dict(rules=['2.4.47','7.2.58'],root='02.0040',finding='Supported: non-cognitive iṇ is replaced by gam before san, and the iṭ restriction is parasmaipada. jigamiṣeta here is second-person plural parasmaipada, not an ātmanepada form.'),
        dict(rules=['7.4.80'],roots=['10.0277','10.0235'],finding='Supported Curadi intrinsic-causative plus san control: Kāśikā explicitly prints bibhāvayiṣati and yiyāvayiṣati. These are not inherited o-abhyāsa intensive inputs.'),
        dict(rules=['7.4.87','7.4.88'],root='01.0608',finding='Supported negative control: commentary explicitly applies nuk and a→u to yaN and yaNluk phal, printing pamphulyate and pamphulīti.'),
        dict(rules=['3.1.29','6.4.78'],root='01.1166',finding='The dictionary citation ṛti is correctly reduced to consonant-final ṛt before īyaṅ. The i→iy substitution before dissimilar ṛ is supported. Neither is the concern below.')],
      unresolved=dict(code='01.1166',operations=['san'],kind='Potential omitted accepted no-īyaṅ branch in sārvadhātuka finite tenses',
        source_reading='3.1.31 Kāśikā makes āya/īyaṅ/ṇiṅ optional when an ārdhadhātuka is intended. Nyāsa explicitly locates the option before suffix introduction. 3.1.7 Kāśikā expressly states that desiderative san is ārdhadhātuka, unlike preceding lexical san.',
        trace_reading='Lat+san obligatorily begins 3.1.29 ṛt+īyaṅ; Lut+san has both that branch and 3.1.31 ṛt without īyaṅ, before 3.1.7 san. Engine optionality therefore appears to depend on the outer finite tense even when san is already intended.',
        proposal='Coordinator independently assess exact 01.1166 + single-san accepted-union completeness. Do not patch gold or infer an unattested replacement string. No proposed blanket āyādi exclusion.',
        pilot07_ids=[t['id'] for t in suspect],pilot07_tasks=suspect,
        candidate03_affected_ids=[t['id'] for t in candidate if t['dhatu']['code']=='01.1166'],historical_root_inputs=old),
      frozen_files_changed=False)
    atomic_json(B/'source-rule-review.json', report)
    print(json.dumps(dict(output=str(B/'source-rule-review.json'),pilot07_ids=[t['id'] for t in suspect],candidate_affected=report['unresolved']['candidate03_affected_ids'],historical_root_inputs=len(old)),indent=2))

if __name__=='__main__': main()
