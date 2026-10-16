"""Small common edits to the frozen table templates after a fresh refusal."""
from data.engine.evaluation import experiment_opus_uniform as e
from data.engine.evaluation.opus_uniform_table_candidates import TITLES


def candidates(original_table):
    result = {'uniform_table': original_table, 'table_question': {}, 'table_exercise': {}, 'table_rules_first': {}}
    for f, text in original_table.items():
        first, rest = text.split('\n\n', 1)
        result['table_question'][f] = f'What is the Sanskrit {TITLES[f]} for the grammatical inputs below?\n\n' + rest
        result['table_exercise'][f] = f'Sanskrit grammar exercise\n\nTask: {TITLES[f]}.\n\n' + rest
        before_answer, answer = rest.split('Write ONLY the final form', 1)
        inputs, rules = before_answer.rstrip().rsplit('\n\n', 1)
        result['table_rules_first'][f] = first + '\n\n' + rules + '\n\n' + inputs + '\n\nWrite ONLY the final form' + answer
        for v in result:
            if f in result[v]:
                assert e.fields(text) == e.fields(result[v][f])
                assert text.split('Write ONLY the final form', 1)[1] == result[v][f].split('Write ONLY the final form', 1)[1]
    return result


if __name__ == '__main__':
    original = e.read_json(e.FOLDER / 'table-candidates.json')['uniform_table']
    variants = candidates(original)
    for v, templates in variants.items():
        folder = e.FOLDER / 'tested-templates' / v
        folder.mkdir(parents=True, exist_ok=True)
        for f, text in templates.items():
            e.base.atomic_write(folder / f'vp_{f}.txt', text)
    e.common.write_json(e.FOLDER / 'followup-candidates.json', variants)
    print('Prepared three small uniform changes plus the frozen control, offline.')
