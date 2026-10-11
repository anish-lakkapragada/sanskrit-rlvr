"""Reviewed lexical inputs for the current creation-task scope (SLP1)."""

# These six prefixes cover all current experiments. In particular, aspirated
# bh is B in SLP1: aBi is valid; the IAST-like spelling abhi is not this prefix.
REVIEWED_PREFIXES = frozenset({"pra", "sam", "ni", "vi", "upa", "aBi"})


def validate_prefixes(prefixes):
    if not isinstance(prefixes, list) or any(p not in REVIEWED_PREFIXES for p in prefixes):
        raise ValueError(f"Unknown or unreviewed SLP1 upasarga: {prefixes!r}")


def input_issue(task):
    if task.get('task_type') == 'cartesian_4d':
        return '4D task unexpectedly contains a derivation' if 'derivation' in task else None
    try:
        validate_prefixes(task["derivation"]["prefixes"])
    except (KeyError, ValueError) as error:
        return str(error)
    return None
