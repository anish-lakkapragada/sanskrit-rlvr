"""Build a read-only diversity view from the frozen 1,800-question candidate."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from finetune.prompts import slp1_to_devanagari

BASE = ROOT / 'benchmarks/parallel-search-20261007/four_d-90'
GANAS = ['Bhvadi', 'Adadi', 'Juhotyadi', 'Divadi', 'Svadi', 'Tudadi', 'Rudhadi', 'Tanadi', 'Kryadi', 'Curadi']
LAKARAS = ['Lat', 'Lit', 'Lut', 'Lrt', 'Lot', 'Lan', 'VidhiLin', 'AshirLin', 'Lun', 'Lrn']
LA_LABELS = ['Present', 'Perfect', 'Periph. future', 'Simple future', 'Imperative', 'Imperfect', 'Optative', 'Benedictive', 'Aorist', 'Conditional']
PERSONS = ['Prathama', 'Madhyama', 'Uttama']
NUMBERS = ['Eka', 'Dvi', 'Bahu']


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tasks_path = BASE / 'candidate-1800-v1/tasks.json'
    tasks = read(tasks_path)
    assert len(tasks) == len({t['id'] for t in tasks}) == 1800
    by_family = defaultdict(list)
    coordinates = Counter()
    for task in tasks:
        assert set(task['morphology']) == {'lakara', 'prayoga', 'purusha', 'vacana'}
        assert task['campaign']['construction'] == 'ordinary_conjugation'
        assert task['morphology']['prayoga'] == 'Kartari'
        by_family[task['campaign']['root_family']].append(task)
        coordinates[tuple(task['morphology'][k] for k in ('lakara', 'purusha', 'vacana'))] += 1
    families = []
    for key, group in sorted(by_family.items(), key=lambda kv: (-len(kv[1]), kv[1][0]['dhatu']['code'])):
        d = group[0]['dhatu']
        matrix = [0] * 90
        for task in group:
            m = task['morphology']
            index = LAKARAS.index(m['lakara']) * 9 + PERSONS.index(m['purusha']) * 3 + NUMBERS.index(m['vacana'])
            matrix[index] += 1
        assert max(matrix) == 1, 'A root/coordinate task was duplicated'
        families.append(dict(key=key, code=d['code'], citation=slp1_to_devanagari(d['aupadeshika']),
                             slp=d['aupadeshika'], gana=d['gana'], meaning=slp1_to_devanagari(d['artha']),
                             n=len(group), cell=group[0]['campaign']['sampling_cell']['label'], matrix=matrix))
    all_matrix = [sum(f['matrix'][i] for f in families) for i in range(90)]
    assert len(families) == 755 and len(coordinates) == 90 and min(all_matrix) > 0
    components = []
    for label, title in [('short_adanta_non_aorist', 'Short-stem class 10 · non-aorist'),
                         ('other_adanta_aorist', 'Other class 10 · aorist'),
                         ('broad_non_curadi', 'Other nine verb classes')]:
        fs = [f for f in families if f['cell'] == label]
        components.append(dict(key=label, title=title, roots=len(fs), n=sum(f['n'] for f in fs),
                               min_per_root=min(f['n'] for f in fs), max_per_root=max(f['n'] for f in fs)))
    status_path = BASE / 'final1800-64k-01/astra-infrastructure-carry-01/source-adjudication/current-audit-summary.json'
    status = read(status_path)
    result_path = ROOT / status['applied_source_layer']['analysis_path']
    assert sha(result_path) == status['applied_source_layer']['analysis_sha256']
    result = read(result_path)
    stats = dict(n=1800, families=755, dictionary_entries=len({t['dhatu']['code'] for t in tasks}),
                 distinct_citation_strings=len({t['dhatu']['aupadeshika'] for t in tasks}),
                 per_family_question_distribution=dict(sorted(Counter(f['n'] for f in families).items())),
                 effective_families_inverse_simpson=1800**2 / sum(f['n']**2 for f in families),
                 selected_coordinate_tuples=90, active_coordinate_reference_grid=90,
                 coordinate_tuple_count_range=[min(all_matrix), max(all_matrix)],
                 aorist_questions=sum(t['morphology']['lakara'] == 'Lun' for t in tasks),
                 voice_counts=dict(Counter(t['morphology']['prayoga'] for t in tasks)),
                 person_counts=dict(Counter(t['morphology']['purusha'] for t in tasks)),
                 number_counts=dict(Counter(t['morphology']['vacana'] for t in tasks)),
                 scores={p: result['models'][p]['statistics']['all_request'] for p in ('Anthropic', 'OpenAI')},
                 tasks_sha256=sha(tasks_path), source_analysis_sha256=sha(result_path), benchmark_ready=False)
    classes = [dict(gana=g, class_number=i + 1, n=sum(f['n'] for f in families if f['gana'] == g),
                    roots=sum(f['gana'] == g for f in families)) for i, g in enumerate(GANAS)]
    data = dict(stats=stats, components=components, classes=classes, families=families,
                lakaras=LAKARAS, lakara_labels=LA_LABELS, persons=PERSONS, numbers=NUMBERS, all_matrix=all_matrix,
                person_number_counts=[sum(all_matrix[l * 9 + j] for l in range(10)) for j in range(9)],
                held_codes=['01.0150', '01.0248', '01.0946', '01.0253', '01.0922', '01.0923'],
                critical_source_code='10.0481')
    out = ROOT / 'benchmarks/visualizations'
    out.mkdir(exist_ok=True)
    summary = ROOT / 'benchmarks/analysis/vp-bench-diversity.json'
    summary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    template = (ROOT / 'misc/vp_diversity.template.html').read_text()
    assert template.count('__VP_DIVERSITY_DATA__') == 1
    fragment = template.replace('__VP_DIVERSITY_DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c'))
    assert len(fragment.encode()) < 1_000_000
    (out / 'vp-bench-diversity.html').write_text(fragment)
    print(json.dumps({'n': len(tasks), 'families': len(families), 'fragment_bytes': len(fragment.encode()),
                      'components': components, 'classes': classes}, indent=2))


if __name__ == '__main__':
    main()
