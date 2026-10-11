"""Independent dhatus, using the established Sanskrit creation template."""
from misc.vp_compositional_prompt_v4 import render as render_form


def render(task):
    prompts = [render_form(f) for f in task['forms']]
    intro = prompts[0].split('=== Your task ===')[0]
    intro = intro.replace('Derive the requested conjugated verb form',
                          'Derive each requested conjugated verb form')
    intro = intro.replace(
        'Write ONLY the final conjugated verb form, in Devanagari script, inside\n'
        '<answer></answer> tags. If several forms are valid, give exactly one.\n'
        'Do not include any text outside the answer tags.',
        'Write ONLY the final conjugated verb forms, in Devanagari script, inside\n'
        'one <answer></answer> block. Give one form per line, in the listed order.\n'
        'If several forms are valid, give exactly one for each requested form.\n'
        'Do not number the answers or include any text outside the answer tags.')
    fields = []
    for i, prompt in enumerate(prompts, 1):
        body = prompt.split('=== Your task ===', 1)[1].strip()
        body = body.replace('   (Dhatupatha citation form, anubandha markers included)', '')
        fields.append(f'Form {i}:\n{body}')
    return intro + '=== Your task ===\n\n' + '\n\n'.join(fields) + '\n'
