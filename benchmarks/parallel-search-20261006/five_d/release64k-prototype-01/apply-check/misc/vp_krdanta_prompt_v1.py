"""One-form creation of an inflected verbal derivative."""
from finetune.prompts import slp1_to_devanagari as deva, GANA_EN, VACANA_EN
from misc.vp_compositional import OPERATIONS

KRT_LABELS = {
    'Satf':'शतृ (present active participle; from the present tense)',
    'tfc':'तृच् (agent noun, one who performs the action)',
    'ktavatu':'क्तवतु (past active participle, one who has performed the action)',
}
LINGA = {'Pum':'masculine','Stri':'feminine','Napumsaka':'neuter'}
VIBHAKTI = {'Prathama':'nominative','Dvitiya':'accusative','Trtiya':'instrumental',
            'Caturthi':'dative','Panchami':'ablative','Sasthi':'genitive',
            'Saptami':'locative','Sambodhana':'vocative'}


def render(task):
    root, d, m = task['dhatu'], task['derivation'], task['morphology']
    prefixes = ' + '.join(deva(p) for p in d['prefixes']) or 'none'
    operations = ', followed by '.join(OPERATIONS[x] for x in d['sanadi']) or 'none'
    return f'''You are an expert in Sanskrit grammar (vyakarana).

Derive the requested inflected verbal noun or adjective (krdanta) from the Sanskrit
verbal root (dhatu, given in Devanagari in its Dhatupatha citation form, anubandha
markers included), its verb class (gana), and its traditional meaning (artha).
The sanadi suffixes specify the derived root, in innermost-to-outermost order.
The krt suffix then forms the noun or adjective; inflect it for the requested
gender (linga), case (vibhakti), and number (vacana). Include the listed prefixes
and regular sandhi in the final form. Each grammatical term is glossed in English.

Write ONLY the final inflected form, in Devanagari script, inside
<answer></answer> tags. If several forms are valid, give exactly one.
Do not include any text outside the answer tags.

=== Your task ===

dhatu (Sanskrit verbal root): {deva(root['aupadeshika'])} (Dhatupatha citation form, anubandha markers included)
gana (verb class): {root['gana']} ({GANA_EN[root['gana']]})
artha (traditional meaning): {deva(root['artha'])}
upasarga (Sanskrit verbal prefixes, in order): {prefixes}
sanadi (Sanskrit derived-root suffixes, innermost first): {operations}

Required form:
- krt (verbal derivative suffix): {KRT_LABELS[m['krt']]}
- krt_artha (semantic role): Kartari (the agent of the action)
- linga (gender): {m['linga']} ({LINGA[m['linga']]})
- vibhakti (case): {m['vibhakti']} ({VIBHAKTI[m['vibhakti']]})
- vacana (number): {m['vacana']} ({VACANA_EN[m['vacana']]})
'''
