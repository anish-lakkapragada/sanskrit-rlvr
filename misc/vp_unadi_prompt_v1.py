"""Creation of a traditional unadi nominal stem, without invented inflection."""
from finetune.prompts import slp1_to_devanagari as deva, GANA_EN


def render(task):
    d = task['dhatu']
    return f'''You are an expert in Sanskrit grammar (vyakarana).

Derive the requested nominal stem (pratipadika) from the Sanskrit verbal root
(dhatu, given in Devanagari in its Dhatupatha citation form, anubandha markers
included), its verb class (gana), its traditional meaning (artha), and the
specified unadi suffix (from the traditional five-chapter Unadipatha).
Use the traditional unadi derivation, including its prescribed stem changes.
The requested answer is the uninflected nominal stem, before case/number endings.
Each Sanskrit grammatical term is glossed in parentheses in English.

Write ONLY the final nominal stem, in Devanagari script, inside
<answer></answer> tags. If several forms are valid, give exactly one.
Do not include any text outside the answer tags.

=== Your task ===

dhatu (Sanskrit verbal root): {deva(d['aupadeshika'])} (Dhatupatha citation form, anubandha markers included)
gana (verb class): {d['gana']} ({GANA_EN[d['gana']]})
artha (traditional meaning): {deva(d['artha'])}
upasarga (Sanskrit verbal prefixes): none

Required form:
- unadi (nominal derivative suffix, anubandha markers included): {deva(task['morphology']['unadi_aupadeshika'])}
- pada level: pratipadika (uninflected nominal stem)
'''
