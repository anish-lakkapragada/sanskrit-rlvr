"""Public-fields-only word modification prompt, version 1."""
from misc.vp_sanskrit_prompt_v1 import LAKARAS, PERSONS, NUMBERS
VOICES={'Kartari':'कर्तरि','Karmani':'कर्मणि','Bhave':'भावे'}

def coordinates(m):
    return (f"लकारः — {LAKARAS[m['lakara']]}\nप्रयोगः — {VOICES[m['prayoga']]}\n"
            f"पुरुषः — {PERSONS[m['purusha']]}\nवचनम् — {NUMBERS[m['vacana']]}\n")

def render(task):
    # Intentionally never access identity, root, class, meaning, recipe or gold.
    return ("संस्कृतव्याकरणप्रश्नः।\n\nदत्तस्य तिङन्तरूपस्य लक्ष्यनिर्देशानुसारं रूपान्तरं लिखत।\n"
            "लौकिकधातुपाठानुसारं सामान्यं रूपम् अपेक्षितम्। उपसर्गं सनादिप्रत्ययं च मा योजयत।\n"
            "सिद्धेषु रूपेष्वेकमेव देवनागरीलिप्या <answer></answer> इत्येतयोर्मध्ये लिखत।\n"
            "अन्यं पाठं मा लिखत।\n\nदत्तं रूपम् — "+task['source_form_devanagari']+
            "\nदत्तरूपस्य निर्देशाः\n"+coordinates(task['source_morphology'])+
            "\nलक्ष्यरूपस्य निर्देशाः\n"+coordinates(task['target_morphology']))
