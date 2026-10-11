"""Explicit Sanskrit-language wording for paired completion diagnostics."""
from finetune.prompts import slp1_to_devanagari as deva

GANAS = dict(zip(['Bhvadi','Adadi','Juhotyadi','Divadi','Svadi','Tudadi','Rudhadi','Tanadi','Kryadi','Curadi'],
                 ['भ्वादिः','अदादिः','जुहोत्यादिः','दिवादिः','स्वादिः','तुदादिः','रुधादिः','तनादिः','क्र्यादिः','चुरादिः']))
LAKARAS = dict(zip(['Lat','Lit','Lut','Lrt','Let','Lot','Lan','VidhiLin','AshirLin','Lun','Lrn'],
                   ['लट्','लिट्','लुट्','लृट्','लेट्','लोट्','लङ्','विधिलिङ्','आशीर्लिङ्','लुङ्','लृङ्']))
OPS = {'yaN':'यङ्','Ric':'णिच्','san':'सन्'}
PERSONS = {'Prathama':'प्रथमपुरुषः','Madhyama':'मध्यमपुरुषः','Uttama':'उत्तमपुरुषः'}
NUMBERS = {'Eka':'एकवचनम्','Dvi':'द्विवचनम्','Bahu':'बहुवचनम्'}


def root_fields(d):
    return f"धातुः — {deva(d['aupadeshika'])}\nगणः — {GANAS[d['gana']]}\nअर्थः — {deva(d['artha'])}\n"


def render(task):
    if task['task_type'] == 'unadi_creation':
        return '''संस्कृतव्याकरणप्रश्नः।

अधोलिखितात् धातोः निर्दिष्टेन उणादिप्रत्ययेन पञ्चपाद्युणादिपाठानुसारं सिद्धं प्रातिपदिकं साधयत।
धातुः धातुपाठोपदेशरूपेण इत्संज्ञकवर्णैः सह दत्तः। प्रत्ययेऽपि इत्संज्ञकवर्णाः दत्ताः।
विभक्तिप्रत्ययं मा योजयत। सिद्धेषु रूपेष्वेकमेव देवनागरीलिप्या
<answer></answer> इत्येतयोर्मध्ये लिखत। अन्यं पाठं मा लिखत।

''' + root_fields(task['dhatu']) + 'उपसर्गः — नास्ति\nउणादिप्रत्ययः — ' + deva(task['morphology']['unadi_aupadeshika']) + '\nअपेक्षितं रूपम् — प्रातिपदिकम्\n'
    if task['task_type'] != 'finite_bundle':
        raise ValueError('Unreviewed Sanskrit prompt task type')
    text = '''संस्कृतव्याकरणप्रश्नाः।

प्रत्येकस्य प्रश्नस्य निर्दिष्टं तिङन्तरूपं साधयत। धातवः धातुपाठोपदेशरूपेण इत्संज्ञकवर्णैः सह दत्ताः।
उपसर्गान् तथा सनादिप्रत्ययान् निर्दिष्टक्रमेण योजयत। सनादिप्रत्ययेषु प्रथमं लिखितः प्रत्ययः प्रथमं योजनीयः।
अन्तिमानि रूपाणि देवनागरीलिप्या <answer></answer> इत्येतयोर्मध्ये लिखत।
प्रत्येकस्य प्रश्नस्य एकमेव सिद्धं रूपं पृथक् पङ्क्तौ क्रमशो लिखत। उत्तराणां क्रमाङ्कान् अन्यं वा पाठं मा लिखत।

'''
    for i,f in enumerate(task['forms'],1):
        d,m = f['derivation'],f['morphology']
        text += f"प्रश्नः {i}\n" + root_fields(f['dhatu'])
        text += 'उपसर्गाः (क्रमेण) — ' + (' → '.join(map(deva,d['prefixes'])) or 'न सन्ति') + '\n'
        text += 'सनादिप्रत्ययाः (क्रमेण) — ' + (' → '.join(OPS[x] for x in d['sanadi']) or 'न सन्ति') + '\n'
        text += f"लकारः — {LAKARAS[m['lakara']]}\nप्रयोगः — कर्तरि\nपदम् — परस्मैपदम्\nपुरुषः — {PERSONS[m['purusha']]}\nवचनम् — {NUMBERS[m['vacana']]}\n\n"
    return text
