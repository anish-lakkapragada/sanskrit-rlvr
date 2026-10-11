"""Field-based extension of the established verbal-derivative task template."""
from finetune.prompts import slp1_to_devanagari as deva, GANA_EN, VACANA_EN
from misc.vp_compositional import OPERATIONS
from misc.vp_samasa_prompt_v1 import CASES


def render(task):
    m = task['morphology']
    text = '''You are an expert in Sanskrit grammar (vyakarana).

Derive the requested inflected compound from the Sanskrit verbal roots (dhatus,
given in Devanagari in their Dhatupatha citation forms, anubandha markers included),
their verb classes (gana), and their traditional meanings (artha).
The sanadi suffixes specify each derived root, in innermost-to-outermost order.
The krt suffix forms a participle denoting the agent of that action. Form the
specified compound from these participles and inflect it for the requested
gender (linga), case (vibhakti), and number (vacana), with regular sandhi.
Each grammatical term is glossed in English.

Write ONLY the final inflected form, in Devanagari script, inside
<answer></answer> tags. If several forms are valid, give exactly one.
Do not include any text outside the answer tags.

=== Your task ===

'''
    for i, member in enumerate(task['members'], 1):
        d = member['dhatu']
        operations = ', followed by '.join(OPERATIONS[x] for x in member['sanadi'])
        text += f'''Member {i}:
dhatu (Sanskrit verbal root): {deva(d['aupadeshika'])} (Dhatupatha citation form, anubandha markers included)
gana (verb class): {d['gana']} ({GANA_EN[d['gana']]})
artha (traditional meaning): {deva(d['artha'])}
upasarga (Sanskrit verbal prefixes, in order): none
sanadi (Sanskrit derived-root suffixes, innermost first): {operations}

'''
    return text + f'''Required form:
- krt (verbal derivative suffix for each member): शतृ (present active participle; from the present tense)
- krt_artha (semantic role): Kartari (the agent of the action)
- samasa (compound type): itaretara-dvandva (coordinative compound)
- samasa_artha (meaning): distinct male agents of equal rank, jointly engaged in an activity
- member order: as listed above
- linga (gender): Pum (masculine)
- vibhakti (case): {m['vibhakti']} ({CASES[m['vibhakti']]})
- vacana (number): {m['vacana']} ({VACANA_EN[m['vacana']]})
'''
