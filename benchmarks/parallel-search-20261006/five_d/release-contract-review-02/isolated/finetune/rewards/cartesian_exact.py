"""Isolated TRL interface for the frozen Cartesian exact-union scorer."""
from misc.vp_goal_dataset import exact_reward
from finetune.rewards import register


def assistant_text(completion):
    """Accept standard strings or one unambiguous TRL assistant message."""
    if isinstance(completion,str):
        return completion
    if not isinstance(completion,list) or len(completion)!=1:
        return None
    message=completion[0]
    if (not isinstance(message,dict) or set(message)!={'role','content'}
            or message['role']!='assistant' or not isinstance(message['content'],str)):
        return None
    return message['content']


@register('vp_cartesian_exact')
def vp_cartesian_exact(prompts,completions,gold_devanagari,**kwargs):
    if len(completions)!=len(gold_devanagari):
        raise ValueError('Reward batch alignment changed')
    return [exact_reward(assistant_text(completion),gold)
            for completion,gold in zip(completions,gold_devanagari)]
