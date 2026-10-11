"""Compact field template; citation and prefix information stated once."""
from misc.vp_samasa_prompt_v2 import render as render_fields


def render(task):
    text = render_fields(task).replace(
        ' (Dhatupatha citation form, anubandha markers included)', '')
    text = text.replace('upasarga (Sanskrit verbal prefixes, in order): none\n', '')
    return text.replace('Required form:\n',
                        'upasarga (Sanskrit verbal prefixes for every member): none\n\nRequired form:\n')
