"""Offline, consistent table layouts derived from the original v2 task fields."""
from data.engine.evaluation import experiment_opus_uniform as e

TITLES = {'tinanta': 'conjugated verb form', 'krdanta': 'krt derivative',
          'taddhitanta': 'taddhita derivative', 'subanta': 'inflected nominal form'}
LABELS = {
    'dhatu (Sanskrit verbal root)': 'Verb in Dhatupatha citation form',
    'gana (verb class)': 'Verb class', 'artha (traditional meaning)': 'Traditional meaning',
    'lakara (tense/mood)': 'Tense or mood', 'prayoga (voice)': 'Voice',
    'purusha (person)': 'Person', 'vacana (number)': 'Number',
    'krt (primary suffix)': 'Primary suffix',
    'pratipadika (nominal stem)': 'Nominal stem',
    'linga (gender)': 'Gender', 'vibhakti (case)': 'Case',
}


def templates(originals, technical_labels=False):
    result = {}
    for f, original in originals.items():
        intro, inputs = original.split('=== Your task ===', 1)
        answer = 'Write ONLY the final form' + intro.split('Write ONLY the final form', 1)[1].rstrip()
        extra = []
        if f == 'taddhitanta' and not technical_labels:
            # Exact previously successful table, now with the same structure in all families.
            rows = [('Nominal stem', '{stem_deva}'), ('Interpretation of the stem', '{base_interpretation}'),
                    ('Taddhita affix', '{suffix_deva}'), ('Technical identifier in SLP1', '{suffix_id}')]
            rules = ('Give the derived nominal stem or complete indeclinable without adding case or number endings. '
                     'Any meaning licensed for this affix is acceptable.')
        else:
            rows = []
            for line in inputs.strip().splitlines():
                line = line.removeprefix('- ')
                if ': ' in line:
                    label, value = line.split(': ', 1)
                    rows.append((label if technical_labels else LABELS.get(label, label), value))
                elif line in ('{prefixes_block}', '{participle_block}'):
                    extra.append(line)
                elif line not in ('', 'Required form:'):
                    raise ValueError(line)
            rules = e.RULES[f]
        table = '| Grammatical input | Value |\n| --- | --- |\n'
        table += ''.join(f'| {label} | {value} |\n' for label, value in rows)
        # Optional prefix and participle lines stay renderer-compatible, verbatim.
        if extra:
            table += '\n' + '\n'.join(extra) + '\n'
        result[f] = f'Form the Sanskrit {TITLES[f]} described in this table.\n\n' + table.rstrip() + '\n\n' + rules + '\n\n' + answer + '\n'
        assert e.fields(original) == e.fields(result[f])
    return result


if __name__ == '__main__':
    m = e.read_json(e.FOLDER / 'manifest.json')
    variants = {'uniform_table': templates(m['original_templates']),
                'uniform_table_technical': templates(m['original_templates'], True)}
    for v, family_templates in variants.items():
        folder = e.FOLDER / 'tested-templates' / v
        folder.mkdir(parents=True, exist_ok=True)
        for f, text in family_templates.items():
            e.base.atomic_write(folder / f'vp_{f}.txt', text)
    e.common.write_json(e.FOLDER / 'table-candidates.json', variants)
    print('Prepared two uniform table variants offline.')
