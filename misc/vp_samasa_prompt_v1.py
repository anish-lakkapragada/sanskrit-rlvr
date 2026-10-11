"""One-word creation of a specified coordinative compound of verbal derivatives."""
from finetune.prompts import slp1_to_devanagari as deva, GANA_EN, VACANA_EN
from misc.vp_compositional import OPERATIONS

CASES = {'Dvitiya':'accusative','Trtiya':'instrumental','Caturthi':'dative',
         'Panchami':'ablative','Sasthi':'genitive','Saptami':'locative'}


def render(task):
    m = task['morphology']
    lines = ['You are an expert in Sanskrit grammar (vyakarana).', '',
        'Construct the requested inflected Sanskrit compound, in Devanagari.',
        'Each listed Sanskrit verbal root (dhatu) describes a different male participant.',
        'For each dhatu, form the specified derived verb and its present active participle',
        '(shatr / शतृ), used substantivally for that participant. The participants act together.',
        'Combine these participant designations into one itaretara-dvandva (coordinative',
        'compound meaning both/all of them), in the listed order, and inflect the compound',
        'for the requested masculine case and number. The participants have equal rank.',
        'Apply the regular compound formation and sandhi rules.', '',
        'Write ONLY the final inflected compound, in Devanagari script, inside',
        '<answer></answer> tags. If several forms are valid, give exactly one.',
        'Do not include any text outside the answer tags.', '', '=== Your task ===', '']
    for i, member in enumerate(task['members'],1):
        d = member['dhatu']
        lines.extend([f'{i}. dhatu (Sanskrit verbal root): {deva(d["aupadeshika"])} (Dhatupatha citation; anubandha markers included)',
                      f'   gana (verb class): {d["gana"]} ({GANA_EN[d["gana"]]})',
                      f'   artha (traditional meaning): {deva(d["artha"])}',
                      '   sanadi (Sanskrit grammatical suffixes, innermost first): '+', followed by '.join(OPERATIONS[x] for x in member['sanadi'])])
    lines.extend(['', 'upasarga (Sanskrit verbal prefixes): none',
                  'krt (participial suffix for every participant): Satf / शतृ (present active)',
                  'samasa (compound type): itaretara-dvandva',
                  'linga (gender): Pum (masculine)',
                  f'vibhakti (case): {m["vibhakti"]} ({CASES[m["vibhakti"]]})',
                  f'vacana (number): {m["vacana"]} ({VACANA_EN[m["vacana"]]})'])
    return '\n'.join(lines)+'\n'
