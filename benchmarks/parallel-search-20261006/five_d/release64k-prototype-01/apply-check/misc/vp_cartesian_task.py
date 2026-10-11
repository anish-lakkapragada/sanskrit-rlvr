"""Shared generation and mechanical validation for exact 4D/5D creation tasks."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from functools import lru_cache

import vidyut
from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import Lakara, Pada, Prayoga, Purusha, Sanadi, Vacana, Vyakarana

from finetune.prompts import slp1_to_devanagari
from misc import vp_campaign_candidates as candidates
from misc.vp_cartesian_prompt_v1 import render
from misc.vp_cartesian_prompt_v2 import render as render_v2
from misc.vp_cartesian_prompt_v3 import render as render_v3
from misc.vp_compositional import OPERATIONS

COORDINATES = {'lakara', 'prayoga', 'purusha', 'vacana'}
GRAMMAR = Vyakarana()
UNVERIFIED_LEXICAL_CODES = {'10.0205', '10.0206', '10.0222', '10.0226'}
VEDIC_ONLY_JUHOTYADI_CODES = frozenset(f'03.{n:04d}' for n in range(15, 27) if n != 17)
VEDIC_ONLY_SVADI_CODES = frozenset(f'05.{n:04d}' for n in range(29, 39) if n != 33)
VEDIC_ONLY_ADADI_CODES = frozenset(f'02.{n:04d}' for n in range(71, 75))
UNRESOLVED_CLASSICAL_SVADI_CODES = frozenset({'05.0013', '05.0014', '05.0015'})
NOMINAL_ONLY_USAGE_CODES = {'01.1088'}


def lexical_identity(entry):
    return entry.dhatu.aupadeshika, candidates.name(entry.dhatu.gana), entry.artha


@lru_cache(maxsize=1)
def ambiguous_lexical_identities():
    """Visible citation/class/meaning must not conceal different subgroup inputs."""
    groups = defaultdict(set)
    for entry in candidates.load_entries():
        groups[lexical_identity(entry)].add(repr(entry.dhatu))
    return frozenset(identity for identity, variants in groups.items() if len(variants) > 1)


def entry_scope_issue(entry):
    if entry.dhatu.prefixes or entry.dhatu.sanadi:
        return 'Dictionary entry has hidden prefixes or sanadi'
    if lexical_identity(entry) in ambiguous_lexical_identities():
        return 'Visible dictionary identity has ambiguous intrinsic grammar'
    if entry.code in UNVERIFIED_LEXICAL_CODES:
        return 'Unverified exact Akusmiya lexical reading in audited primary editions'
    if entry.code in VEDIC_ONLY_JUHOTYADI_CODES:
        return 'Source-marked Vedic-only Juhotyadi entry outside current classical scope'
    if entry.code in VEDIC_ONLY_SVADI_CODES:
        return 'Source-marked Vedic-only Svadi entry outside current classical scope'
    if entry.code in VEDIC_ONLY_ADADI_CODES:
        return 'Source-marked Vedic-only Adadi entry outside current classical scope'
    if entry.code in UNRESOLVED_CLASSICAL_SVADI_CODES:
        return 'Unresolved classical scope for Svadi pr/spr/smr: sources mark Vedic or predominantly Vedic'
    if entry.code in NOMINAL_ONLY_USAGE_CODES:
        return 'Source restricts this lexical entry to nominal formations; finite use unverified'
    if entry.code == '04.0127':
        return 'Dictionary svid citation omits source-required root accent and changes anit classification'
    return None


@lru_cache(maxsize=1)
def entries_by_code():
    return {entry.code: entry for entry in candidates.load_entries()}


@lru_cache(maxsize=8192)
def intermediate_stem_ends_in_a(code, operations):
    dhatu = entries_by_code()[code].dhatu.with_sanadi([getattr(Sanadi, op) for op in operations])
    return any(p.text.endswith('A') for p in GRAMMAR.derive(dhatu))


@lru_cache(maxsize=4096)
def bare_base_is_am_final(code):
    """Preserve the separate phonological mit prescription for am-final bases."""
    bases = {p.text for p in GRAMMAR.derive(entries_by_code()[code].dhatu)}
    return bool(bases) and all(base.endswith('am') for base in bases)


def oracle_issue(task):
    """Prospective rule-wide quarantines; preserve existing tasks and raw scores.

    Evidence: parallel-search-20261006/{four_d,five_d} oracle reviews and the
    coordinator's oracle-policy-21.json. These do not depend on model answers.
    """
    rules = set(task['campaign']['trace_rule_ids'])
    m = task['morphology']
    if task['dhatu']['code'] == '01.0114' and '6.1.64' in rules:
        return 'Source-prohibited dentalization of the exact shvakka lexical entry'
    if task['dhatu']['code'] in {'10.0303', '10.0304'} and '3.1.28' in rules:
        return 'Intrinsic aya overreach onto distinct Curadi speech entries'
    if (task['dhatu']['code'] == '01.0866' and '8.2.18' in rules
            and any('x' in form or 'X' in form for form in task['gold_slp1'])):
        return 'Scorer lacks source-attested vocalic-l spelling aliases for klrp'
    if rules & {'3.1.5', '3.1.6'}:
        return 'Uncertified meaning condition for lexical san before requested operations'
    if ('8.2.78' in rules and task['dhatu']['code'] in
            {'01.0020', '01.0021', '01.0022', '01.0023', '10.0180'}):
        return 'Uncertified optional short-vowel alternatives to lexical lengthening'
    if (task['dhatu']['code'] == '04.0029' and m['lakara'] == 'Lit'
            and m['purusha'] == 'Madhyama' and m['vacana'] == 'Bahu'
            and '6.4.63' in rules):
        return 'Missing documented dental-dh alternative after diN yuT augmentation'
    if '6.4.123' in rules:
        return 'Uncertified semantic condition for rule 6.4.123'
    if '6.4.91' in rules:
        return 'Uncertified mental-state meaning condition for rule 6.4.91'
    if m['lakara'] == 'Lun' and task['dhatu']['code'] in {'04.0113', '04.0141'}:
        return 'Dictionary citation mismatch in PUSH_ADI aorist membership'
    if (m['prayoga'] in {'Karmani', 'Bhave'} and m['lakara'] in {'Lut', 'Lrt'}
            and {'6.4.62', '6.4.92'} <= rules):
        return 'Incomplete optional Cinvat vowel variants in passive future'
    ops = task.get('derivation', {}).get('sanadi', [])
    if (task['dhatu']['code'] in {'01.0504', '06.0055', '06.0056', '06.0057', '08.0006', '08.0007'}
            and ops and ops[0] in {'yaN', 'yaNluk'} and '7.4.85' in rules):
        return 'Source-required ri augmentation displaced by nasal augmentation in r-bearing intensive'
    if (ops and rules & {'3.1.28', '3.1.29', '3.1.30'} and '3.1.31' not in rules
            and not (task['dhatu']['code'] == '01.0507' and ops == ['san'])):
        return 'Missing optional intrinsic ayadi branch before added ardhadhatuka operation'
    if task['dhatu']['code'] == '02.0039' and ops[:2] == ['yaNluk', 'Ric']:
        return 'Uncertified bru substitution timing after intensive-luk and causative'
    if (task['dhatu']['code'] == '01.1043' and ops[:2] == ['yaN', 'Ric']
            and '6.4.89' in rules):
        return 'Uncertified guh lengthening where inner intensive deletion blocks guna'
    if ops == ['san']:
        if '7.4.7' in rules:
            return 'caN-conditioned r preservation applied inside a desiderative with outer sic'
        if (task['dhatu']['code'] == '01.0262'
                and m['lakara'] in {'Lit', 'Lut', 'Lrt', 'AshirLin', 'Lun', 'Lrn'}):
            return 'Uncertified repeated aj substitution inside an already formed desiderative'
        if task['dhatu']['code'] == '04.0160' and m['lakara'] in {'Lan', 'Lun', 'Lrn'}:
            return 'Repeated rdh vowel replacement after desiderative augmentation'
        if task['dhatu']['code'] == '02.0067':
            return 'Source-required it augmentation absent from polysyllabic jagr desiderative'
    if task['dhatu']['code'] == '06.0012' and ops and ops[0] == 'yaNluk':
        return 'Source-attested vrasc intensive-luk base absent from engine gold'
    if task['dhatu']['code'] == '06.0149' and ops and ops[0] == 'yaNluk':
        return 'Source-attested prcch intensive-luk base absent from engine gold'
    if task['dhatu']['code'] == '02.0007' and set(ops) & {'Ric', 'yaN', 'san'}:
        return 'Unresolved caksh substitution in added sanadi derivation'
    if task['dhatu']['code'] == '01.1014' and rules & {'1.3.92', '7.2.59'}:
        return 'Lexical overreach of VRT_ADI to the distinct moisten entry'
    if 'Ric' in ops and any(op in {'yaN', 'yaNluk'} for op in ops[:ops.index('Ric')]):
        if rules & {'7.4.79', '7.4.80', '7.4.81', '7.4.94', '7.4.95', '8.3.61'}:
            return 'Unresolved rule interaction in nested intensive recipe'
    if 'Ric' in ops and 'yaNluk' in ops[:ops.index('Ric')]:
        if intermediate_stem_ends_in_a(task['dhatu']['code'], tuple(ops[:ops.index('Ric')])):
            return 'Unresolved puK augmentation after A-final intensive-luk stem'
        citation = entries_by_code()[task['dhatu']['code']].dhatu.aupadeshika
        if '7.4.2' in rules and citation.rstrip('\\^').endswith('f~'):
            return 'Uncertified original r-it marker effect after intensive-luk derivation'
        if '6.4.92' in rules and not bare_base_is_am_final(task['dhatu']['code']):
            return 'Uncertified lexical mit transfer after non-am intensive-luk derivation'
        if '7.4.96' in rules:
            return 'Uncertified shtip-designated 7.4.96 effect after intensive-luk derivation'
    return None


def make_task(entry, split, morphology, recipe_id=None, sanadi=None, *, prompt_version=None):
    issue = entry_scope_issue(entry)
    if issue:
        raise ValueError(issue)
    if set(morphology) != COORDINATES:
        raise ValueError('Exactly four inflection coordinates are required')
    if morphology['lakara'] == 'Let':
        raise ValueError('Classical scope excludes Let')
    if morphology['prayoga'] == 'Bhave' and (morphology['purusha'], morphology['vacana']) != ('Prathama', 'Eka'):
        raise ValueError('Impersonal agreement requires third-person singular')
    five_d = recipe_id is not None
    if five_d:
        if not isinstance(recipe_id, str) or not recipe_id or not isinstance(sanadi, list):
            raise ValueError('5D requires a recipe ID and an ordered operation list')
        if any(op not in OPERATIONS for op in sanadi):
            raise ValueError('Only the declared verbal sanadi options are supported')
    elif sanadi not in (None, []):
        raise ValueError('4D cannot add a derivation')
    ops = list(sanadi or [])
    d = entry.dhatu.with_sanadi([getattr(Sanadi, x) for x in ops]) if five_d else entry.dhatu
    m = dict(morphology)
    results = GRAMMAR.derive(Pada.Tinanta(dhatu=d, lakara=getattr(Lakara, m['lakara']),
        prayoga=getattr(Prayoga, m['prayoga']), purusha=getattr(Purusha, m['purusha']),
        vacana=getattr(Vacana, m['vacana'])))
    if not results:
        return None
    gold = sorted({p.text for p in results})
    for form in gold:
        if transliterate(slp1_to_devanagari(form), Scheme.Devanagari, Scheme.Slp1) != form:
            raise ValueError('Gold transliteration does not round-trip')
    dimension = 5 if five_d else 4
    prompt_version = prompt_version or f'cartesian-{dimension}d-v1'
    renderers = {f'cartesian-{dimension}d-v1': render,
                 f'cartesian-{dimension}d-v2-verb': render_v2,
                 f'cartesian-{dimension}d-v3-sanskrit': render_v3}
    if prompt_version not in renderers:
        raise ValueError('Unsupported Cartesian prompt version for this dimension')
    identity = [dimension, entry.code, m, ops]
    digest = hashlib.sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
    task = {'id': f'cart{dimension}-' + digest, 'task_type': f'cartesian_{dimension}d',
            'prompt_version': prompt_version,
            'dhatu': {'code': entry.code, 'aupadeshika': entry.dhatu.aupadeshika,
                      'gana': candidates.name(entry.dhatu.gana), 'artha': entry.artha},
            'morphology': m, 'gold_slp1': gold, 'gold_devanagari': list(map(slp1_to_devanagari, gold)),
            'campaign': {'root_family': candidates.family(entry), 'split': split,
                'construction': recipe_id if five_d else 'ordinary_conjugation',
                'trace_rule_ids': sorted({h.code for p in results for h in p.history
                                          if candidates.name(h.source) == 'Ashtadhyayi'}),
                'minimum_trace_steps': min(len(p.history) for p in results),
                'gold_variants': len(gold), 'vp_version': vidyut.__version__,
                'track': f'{"five" if five_d else "four"}_d',
                'audit_status': 'regeneration_and_roundtrip_only; grammatical_review_required'}}
    if five_d:
        task['derivation'] = {'recipe_id': recipe_id, 'sanadi': ops, 'prefixes': [],
                              'order': 'innermost_to_outermost'}
    task['campaign']['prompt_sha256'] = hashlib.sha256(renderers[prompt_version](task).encode()).hexdigest()
    return task


def validate_task(task, entry, split):
    five_d = task['task_type'] == 'cartesian_5d'
    if task['task_type'] not in {'cartesian_4d', 'cartesian_5d'}:
        raise ValueError('Unsupported task type')
    d = task.get('derivation')
    if not five_d and d is not None:
        raise ValueError('4D must not contain a derivation field')
    if five_d and (not isinstance(d, dict) or set(d) != {'recipe_id', 'sanadi', 'prefixes', 'order'}
                   or d['prefixes'] != [] or d['order'] != 'innermost_to_outermost'):
        raise ValueError('5D must have one recipe and no prefixes')
    expected = make_task(entry, split, task['morphology'], d['recipe_id'] if five_d else None,
                         d['sanadi'] if five_d else None, prompt_version=task['prompt_version'])
    if expected is None:
        raise ValueError('No engine derivation')
    keys = ['id', 'task_type', 'prompt_version', 'dhatu', 'morphology', 'gold_slp1', 'gold_devanagari']
    if five_d:
        keys.append('derivation')
    for key in keys:
        if task[key] != expected[key]:
            raise ValueError('Regenerated Cartesian task disagrees: ' + key)
    for key in expected['campaign']:
        if key != 'audit_status' and task['campaign'].get(key) != expected['campaign'][key]:
            raise ValueError('Regenerated Cartesian metadata disagrees: ' + key)
    issue = oracle_issue(task)
    if issue:
        raise ValueError('Oracle quarantine: ' + issue)
    cell = task['campaign'].get('sampling_cell', {})
    if set(task['campaign']['trace_rule_ids']) & set(cell.get('exclude_rules', [])):
        raise ValueError('Task violates declared rule exclusions')
    if task['dhatu']['gana'] in cell.get('exclude_ganas', []):
        raise ValueError('Task violates declared gana exclusion')
    if 'ganas' in cell and task['dhatu']['gana'] not in cell['ganas']:
        raise ValueError('Task violates declared gana selection')
    rules = set(task['campaign']['trace_rule_ids'])
    if not set(cell.get('require_rules_all', [])) <= rules:
        raise ValueError('Task lacks required grammatical rules')
    if cell.get('require_rules_any') and not rules.intersection(cell['require_rules_any']):
        raise ValueError('Task lacks any of the required grammatical rules')
    if 'transitive_artha_allowlist' in cell and task['dhatu']['artha'] not in cell['transitive_artha_allowlist']:
        raise ValueError('Task is outside the declared lexical meaning scope')
    if five_d and 'recipe_id' in cell and cell['recipe_id'] != d['recipe_id']:
        raise ValueError('Task differs from the declared derivation recipe')
    for field, key in [('lakara', 'lakaras'), ('prayoga', 'prayogas'), ('purusha', 'purushas'), ('vacana', 'vacanas')]:
        if key in cell and task['morphology'][field] not in cell[key]:
            raise ValueError('Task violates sampling cell: ' + key)
