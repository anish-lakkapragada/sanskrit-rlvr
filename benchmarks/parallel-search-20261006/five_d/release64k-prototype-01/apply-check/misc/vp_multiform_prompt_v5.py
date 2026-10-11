"""Minimal multi-form extension of the established high-completion template."""
from misc.vp_compositional_prompt_v4 import render as render_form


def render(task):
    prompts = [render_form(form) for form in task['forms']]
    before_fields, _ = prompts[0].split('upasarga (', 1)
    before_fields = before_fields.replace('Derive the requested conjugated verb form',
                                         'Derive the requested conjugated verb forms')
    before_fields = before_fields.replace(
        'Write ONLY the final conjugated verb form, in Devanagari script, inside\n'
        '<answer></answer> tags. If several forms are valid, give exactly one.\n'
        'Do not include any text outside the answer tags.',
        'Write ONLY the final conjugated verb forms, in Devanagari script, inside\n'
        'one <answer></answer> block. Give one form per line, in the listed order.\n'
        'If several forms are valid, give exactly one for each requested form.\n'
        'Do not number the answers or include any text outside the answer tags.')
    sections = []
    for i, prompt in enumerate(prompts, 1):
        _, fields = prompt.split('upasarga (', 1)
        sections.append(f'Form {i} (from the dhatu specified above):\nupasarga (' + fields)
    return before_fields + '\n'.join(sections)
