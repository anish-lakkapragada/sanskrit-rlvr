"""Sanskrit-language elicitation of the same four/five-coordinate question."""
from misc.vp_sanskrit_prompt_v1 import root_fields, LAKARAS, PERSONS, NUMBERS

OPS = {'yaN': 'यङ्', 'yaNluk': 'यङ्लुक्', 'Ric': 'णिच्', 'san': 'सन्'}
VOICES = {'Kartari': 'कर्तरि', 'Karmani': 'कर्मणि', 'Bhave': 'भावे'}


def render(task):
    if task['task_type'] not in {'cartesian_4d', 'cartesian_5d'}:
        raise ValueError('Unsupported Cartesian question')
    text = '''संस्कृतव्याकरणप्रश्नः।

अधोलिखितात् धातोः निर्दिष्टं तिङन्तरूपं साधयत।
धातुः धातुपाठोपदेशरूपेण इत्संज्ञकवर्णैः सह दत्तः। गणोऽर्थश्च निर्दिष्टौ।
सिद्धेषु रूपेष्वेकमेव देवनागरीलिप्या <answer></answer> इत्येतयोर्मध्ये लिखत।
अन्यं पाठं मा लिखत।

''' + root_fields(task['dhatu'])
    if task['task_type'] == 'cartesian_5d':
        ops = task['derivation']['sanadi']
        text += ('सनादिप्रत्ययान् निर्दिष्टक्रमेण योजयत। प्रथमं लिखितः प्रत्ययः प्रथमं योजनीयः।\n'
                 'सनादिप्रत्ययाः (क्रमेण) — ' + (' → '.join(OPS[x] for x in ops) or 'न सन्ति') + '\n')
    m = task['morphology']
    return text + (f"लकारः — {LAKARAS[m['lakara']]}\nप्रयोगः — {VOICES[m['prayoga']]}\n"
                   f"पुरुषः — {PERSONS[m['purusha']]}\nवचनम् — {NUMBERS[m['vacana']]}\n")
