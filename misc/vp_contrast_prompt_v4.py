"""Format diagnostic: identical Sanskrit questions with ordered-line answers."""
from misc.vp_contrast_prompt_v3 import render as render_previous

JSON_INSTRUCTIONS = '\n'.join([
    'Return ONLY a JSON object inside one <answer></answer> block. Use the row numbers',
    'as string keys and one valid Devanagari form as each value. Include every row exactly once.',
    'Example format for two rows: <answer>{"1":"FORM","2":"FORM"}</answer>.',
    'Do not include explanation. If alternatives are valid, give exactly one per row.',
])
LINE_INSTRUCTIONS = '\n'.join([
    'Write ONLY the requested conjugated verb forms, in Devanagari script,',
    'one form per line in the given order, inside one <answer></answer> block.',
    'If several forms are valid, give exactly one per line.',
    'Do not number the answers or include any text outside the answer tags.',
])


def render(task):
    previous = render_previous(task)
    if previous.count(JSON_INSTRUCTIONS) != 1:
        raise ValueError('Frozen output instructions unexpectedly changed')
    return previous.replace(JSON_INSTRUCTIONS, LINE_INSTRUCTIONS)
