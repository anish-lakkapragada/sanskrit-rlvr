"""Reject scope expansion and bad gold before spending on 4D/5D tasks."""
import copy
import unittest
from types import SimpleNamespace

from finetune.prompts import render_vp_task
from misc import vp_goal as c, oai_batch_eval as io
from misc.vp_campaign_candidates import load_entries, family
from misc.vp_cartesian_task import make_task, entry_scope_issue, oracle_issue
from misc.vp_cartesian_prompt_v1 import render
from misc.vp_goal_validate import validate
from misc.vp_goal_grammar import input_issue


class CartesianScopeTests(unittest.TestCase):
    def test_r_bearing_intensive_gate_preserves_plain_and_other_nasal_bases(self):
        entries = {e.code: e for e in load_entries()}
        for code in ['01.0504', '06.0055', '06.0056', '06.0057', '08.0006', '08.0007']:
            for ops in [['yaN'], ['yaNluk'], ['yaN', 'Ric'], ['yaNluk', 'Ric']]:
                task = make_task(entries[code], 'development', self.four['morphology'], 'control', ops)
                self.assertIn('7.4.85', task['campaign']['trace_rule_ids'])
                self.assertIn('Source-required ri augmentation', oracle_issue(task))
            for ops in [[], ['san'], ['Ric']]:
                task = make_task(entries[code], 'development', self.four['morphology'],
                                 'control' if ops else None, ops or None)
                self.assertIsNone(oracle_issue(task))
        for ops in [['yaN'], ['yaNluk'], ['yaN', 'Ric'], ['yaNluk', 'Ric']]:
            task = make_task(entries['01.1137'], 'development', self.four['morphology'], 'control', ops)
            self.assertIn('7.4.85', task['campaign']['trace_rule_ids'])
            self.assertIsNone(oracle_issue(task))

    @classmethod
    def setUpClass(cls):
        assignments = io.read_json(c.HISTORY / 'family-split.json')['families']
        m = {'lakara': 'Lat', 'prayoga': 'Kartari', 'purusha': 'Prathama', 'vacana': 'Eka'}
        for entry in load_entries():
            if assignments[family(entry)]['split'] != 'development':
                continue
            four = make_task(entry, 'development', m)
            five = make_task(entry, 'development', m, 'causative', ['Ric'])
            if four and five:
                cls.entry, cls.four, cls.five = entry, four, five
                break

    def test_4d_prompt_is_exact_original_template(self):
        self.assertEqual(render(self.four), render_vp_task(self.four, 'v2/vp_task_eval.txt'))
        self.assertIsNone(input_issue(self.four))
        self.assertTrue(validate([self.four, self.five], 'development')['passed_mechanical_checks'])

    def test_hidden_fifth_coordinate_in_4d_is_rejected(self):
        t = copy.deepcopy(self.four)
        t['morphology']['dhatu_pada'] = 'Parasmaipada'
        with self.assertRaisesRegex(ValueError, 'Exactly four'):
            validate([t], 'development')
        t = copy.deepcopy(self.four)
        t['derivation'] = {'sanadi': ['Ric'], 'prefixes': []}
        with self.assertRaisesRegex(ValueError, 'must not contain'):
            validate([t], 'development')

    def test_prefix_cannot_be_hidden_in_5d(self):
        t = copy.deepcopy(self.five)
        t['derivation']['prefixes'] = ['pra']
        with self.assertRaisesRegex(ValueError, 'no prefixes'):
            validate([t], 'development')

    def test_false_gold_and_changed_recipe_are_rejected(self):
        for edit in ['gold', 'recipe']:
            t = copy.deepcopy(self.five)
            if edit == 'gold':
                t['gold_devanagari'] = ['गलत']
            else:
                t['derivation']['sanadi'] = ['san']
            with self.assertRaises(ValueError):
                validate([t], 'development')

    def test_split_and_impersonal_agreement(self):
        with self.assertRaisesRegex(ValueError, 'split violation'):
            validate([self.four], 'test')
        m = dict(self.four['morphology'], prayoga='Bhave', vacana='Bahu')
        with self.assertRaisesRegex(ValueError, 'third-person singular'):
            make_task(self.entry, 'development', m)

    def test_request_uses_the_versioned_cartesian_prompt(self):
        request = c.request(self.five, 'Anthropic', 'explore', 0)
        self.assertEqual(request['params']['messages'][0]['content'], render(self.five))
        self.assertEqual(request['params']['output_config']['effort'], 'xhigh')
        self.assertEqual(request['params']['max_tokens'], 16384)

    def test_wording_probe_preserves_tasks_and_validates_exact_prompt(self):
        for original in [self.four, self.five]:
            dim = 5 if 'derivation' in original else 4
            d = original.get('derivation', {})
            t = make_task(self.entry, 'development', original['morphology'],
                          d.get('recipe_id'), d.get('sanadi'),
                          prompt_version=f'cartesian-{dim}d-v2-verb')
            self.assertTrue(validate([t], 'development')['passed_mechanical_checks'])
            self.assertEqual(t['id'], original['id'])
            self.assertEqual(t['gold_devanagari'], original['gold_devanagari'])
            prompt = c.request(t, 'Anthropic', 'explore', 0)['params']['messages'][0]['content']
            self.assertEqual(prompt, render(original).replace('Sanskrit verbal root', 'Sanskrit verb entry'))
            self.assertNotIn('root', prompt)
            t['campaign']['prompt_sha256'] = original['campaign']['prompt_sha256']
            with self.assertRaisesRegex(ValueError, 'metadata disagrees'):
                validate([t], 'development')

    def test_grammatical_cell_membership_is_enforced(self):
        t = copy.deepcopy(self.four)
        t['campaign']['sampling_cell'] = {'require_rules_all': ['not-a-rule']}
        with self.assertRaisesRegex(ValueError, 'required grammatical rules'):
            validate([t], 'development')

    def test_sanskrit_prompt_preserves_explicit_coordinates_and_operation_order(self):
        t = make_task(self.entry, 'development', self.four['morphology'],
                      'causative_of_intensive', ['yaN', 'Ric'],
                      prompt_version='cartesian-5d-v3-sanskrit')
        self.assertTrue(validate([t], 'development')['passed_mechanical_checks'])
        prompt = c.request(t, 'Anthropic', 'explore', 0)['params']['messages'][0]['content']
        for field in ['धातुः', 'गणः', 'अर्थः', 'लकारः', 'प्रयोगः', 'पुरुषः', 'वचनम्']:
            self.assertIn(field, prompt)
        self.assertIn('यङ् → णिच्', prompt)
        self.assertNotIn('पदम्', prompt)
        self.assertNotIn('उपसर्ग', prompt)

    def test_dictionary_modifiers_and_ambiguous_inputs_are_rejected(self):
        from vidyut.prakriya import Sanadi
        entries = {e.code: e for e in load_entries()}
        for code in ['02.0012', '02.0041', '02.0042', '10.0368',
                     '01.0916', '01.0965', '01.0924', '01.0966',
                     '01.0928', '01.0962', '10.0257', '10.0367',
                     '10.0205', '10.0206', '10.0222', '10.0226']:
            with self.subTest(code=code):
                self.assertIsNotNone(entry_scope_issue(entries[code]))
                with self.assertRaises(ValueError):
                    make_task(entries[code], 'development', self.four['morphology'])
        derived = SimpleNamespace(code=self.entry.code, artha=self.entry.artha,
            dhatu=self.entry.dhatu.with_sanadi([Sanadi.Ric]))
        with self.assertRaisesRegex(ValueError, 'hidden prefixes or sanadi'):
            make_task(derived, 'development', self.four['morphology'], 'desiderative', ['san'])

    def test_passive_quarantine_requires_joint_context(self):
        task = copy.deepcopy(self.five)
        task['morphology'].update(lakara='Lut', prayoga='Karmani')
        for rules in [['6.4.62'], ['6.4.92']]:
            task['campaign']['trace_rule_ids'] = rules
            self.assertIsNone(oracle_issue(task))
        task['campaign']['trace_rule_ids'] = ['6.4.62', '6.4.92']
        self.assertIn('Cinvat', oracle_issue(task))
        task['morphology']['lakara'] = 'Lun'
        self.assertIsNone(oracle_issue(task))

    def test_vedic_subgroup_quarantine_preserves_attested_classical_exception(self):
        entries = {e.code: e for e in load_entries()}
        for n in range(15, 27):
            issue = entry_scope_issue(entries[f'03.{n:04d}'])
            if n == 17:
                self.assertIsNone(issue)
            else:
                self.assertIn('Vedic-only', issue)

    def test_known_incorrect_gold_context_is_rejected_by_full_validator(self):
        assignments = io.read_json(c.HISTORY / 'family-split.json')['families']
        entry = next(e for e in load_entries() if e.code == '05.0018')
        split = assignments[family(entry)]['split']
        task = make_task(entry, split, dict(self.four['morphology'], lakara='Lit',
                                         purusha='Madhyama', vacana='Bahu'))
        self.assertIn('6.4.123', task['campaign']['trace_rule_ids'])
        with self.assertRaisesRegex(ValueError, 'Oracle quarantine'):
            validate([task], split)

    def test_nominal_only_entry_is_excluded_from_both_finite_task_shapes(self):
        entries = {e.code: e for e in load_entries()}
        entry = entries['01.1088']
        for recipe, ops in [(None, None), ('causative_of_intensive', ['yaN', 'Ric'])]:
            with self.assertRaisesRegex(ValueError, 'nominal formations'):
                make_task(entry, 'development', self.four['morphology'], recipe, ops)
        self.assertIsNone(entry_scope_issue(entries['03.0017']))

    def test_svadi_vedic_scope_preserves_classical_kshi(self):
        entries = {e.code: e for e in load_entries()}
        for n in range(29, 39):
            issue = entry_scope_issue(entries[f'05.{n:04d}'])
            if n == 33:
                self.assertIsNone(issue)
            else:
                self.assertIn('Vedic-only Svadi', issue)

    def test_svadi_three_scope_hold_preserves_classical_homonyms(self):
        entries = {e.code: e for e in load_entries()}
        for code in ('05.0013', '05.0014', '05.0015'):
            self.assertIn('Unresolved classical scope', entry_scope_issue(entries[code]))
            for recipe, ops in [(None, None), ('desiderative', ['san'])]:
                with self.assertRaisesRegex(ValueError, 'Unresolved classical scope'):
                    make_task(entries[code], 'development', self.four['morphology'], recipe, ops)
        for code in ('03.0005', '01.1082', '05.0012', '05.0016'):
            self.assertIsNone(entry_scope_issue(entries[code]), code)

    def test_can_conditioned_r_option_does_not_extend_to_san(self):
        entries = {e.code: e for e in load_entries()}
        m = dict(lakara='Lun', prayoga='Kartari', purusha='Prathama', vacana='Eka')
        for code in ('10.0351', '10.0155'):
            san = make_task(entries[code], 'development', m, 'desiderative', ['san'])
            self.assertIn('caN-conditioned', oracle_issue(san))
            ordinary = make_task(entries[code], 'development', m)
            self.assertIn('7.4.7', ordinary['campaign']['trace_rule_ids'])
            self.assertIsNone(oracle_issue(ordinary))
            present = make_task(entries[code], 'development', dict(m, lakara='Lat'),
                                'desiderative', ['san'])
            self.assertIsNone(oracle_issue(present))

    def test_caksh_quarantine_preserves_bare_intensive_luk(self):
        t = copy.deepcopy(self.five)
        t['dhatu']['code'] = '02.0007'
        t['campaign']['trace_rule_ids'] = []
        for ops in [['Ric'], ['yaN'], ['san'], ['yaNluk', 'Ric']]:
            t['derivation']['sanadi'] = ops
            self.assertIn('caksh', oracle_issue(t))
        t['derivation']['sanadi'] = ['yaNluk']
        self.assertIsNone(oracle_issue(t))

    def test_puk_quarantine_uses_intermediate_stem_and_recipe_order(self):
        entries = {e.code: e for e in load_entries()}
        for code in ['01.1079', '03.0009', '01.1077', '01.1051']:
            t = make_task(entries[code], 'development', self.four['morphology'],
                          'causative_of_intensive_luk', ['yaNluk', 'Ric'])
            self.assertIn('puK', oracle_issue(t))
            t['derivation']['sanadi'] = ['yaNluk']
            self.assertIsNone(oracle_issue(t))

    def test_vrt_adi_quarantine_requires_wrong_lexical_entry_and_rule(self):
        t = copy.deepcopy(self.four)
        for code, rules, excluded in [('01.1014', ['7.2.59'], True),
                ('01.1014', [], False), ('01.0864', ['7.2.59'], False)]:
            t['dhatu']['code'] = code
            t['campaign']['trace_rule_ids'] = rules
            self.assertEqual(oracle_issue(t) is not None, excluded)

    def test_semantic_san_and_lexical_lengthening_quarantines(self):
        t = copy.deepcopy(self.four)
        for rule in ['3.1.5', '3.1.6']:
            t['campaign']['trace_rule_ids'] = [rule]
            self.assertIn('meaning condition', oracle_issue(t))
        t['campaign']['trace_rule_ids'] = ['8.2.78']
        for code in ['01.0020', '01.0021', '01.0022', '01.0023', '10.0180']:
            t['dhatu']['code'] = code
            self.assertIn('short-vowel', oracle_issue(t))
        t['dhatu']['code'] = '10.0023'
        self.assertIsNone(oracle_issue(t))

    def test_ding_dhvam_variant_quarantine_is_context_specific(self):
        t = copy.deepcopy(self.four)
        t['dhatu']['code'] = '04.0029'
        t['morphology'].update(lakara='Lit', purusha='Madhyama', vacana='Bahu')
        t['campaign']['trace_rule_ids'] = ['6.4.63']
        self.assertIn('dental-dh', oracle_issue(t))
        t['morphology']['vacana'] = 'Dvi'
        self.assertIsNone(oracle_issue(t))

    def test_mental_state_variant_requires_semantic_certification(self):
        t = copy.deepcopy(self.five)
        t['campaign']['trace_rule_ids'] = ['6.4.91']
        self.assertIn('mental-state', oracle_issue(t))
        t['campaign']['trace_rule_ids'] = ['6.4.90']
        self.assertIsNone(oracle_issue(t))

    def test_nested_rule_quarantine_also_applies_to_intensive_luk(self):
        task = copy.deepcopy(self.five)
        task['campaign']['trace_rule_ids'] = ['7.4.94']
        for intensive in ['yaN', 'yaNluk']:
            task['derivation']['sanadi'] = [intensive, 'Ric']
            self.assertIn('nested intensive', oracle_issue(task))
        task['derivation']['sanadi'] = ['yaNluk']
        self.assertIsNone(oracle_issue(task))

    def test_shvakka_dentalization_quarantine_is_lexically_specific(self):
        entry = next(e for e in load_entries() if e.code == '01.0114')
        task = make_task(entry, 'development', self.four['morphology'])
        self.assertEqual(task['gold_slp1'], ['svakkate'])
        self.assertIn('dentalization', oracle_issue(task))
        task['campaign']['trace_rule_ids'] = []
        self.assertIsNone(oracle_issue(task))
        task['campaign']['trace_rule_ids'] = ['6.1.64']
        task['dhatu']['code'] = '01.0113'
        self.assertIsNone(oracle_issue(task))

    def test_svid_dictionary_quarantine_preserves_distinct_bhvadi_entry(self):
        entries = {e.code: e for e in load_entries()}
        self.assertIn('anit classification', entry_scope_issue(entries['04.0127']))
        self.assertIsNone(entry_scope_issue(entries['01.0845']))
        for recipe, ops in [(None, None), ('desiderative', ['san'])]:
            with self.assertRaisesRegex(ValueError, 'root accent'):
                make_task(entries['04.0127'], 'development', self.four['morphology'], recipe, ops)

    def test_luk_marker_quarantine_preserves_other_742_branches_and_recipe_order(self):
        entries = {e.code: e for e in load_entries()}
        for code in ['01.0615', '01.1009']:
            t = make_task(entries[code], 'development', dict(self.four['morphology'], lakara='Lun'),
                          'causative_of_intensive_luk', ['yaNluk', 'Ric'])
            self.assertIn('7.4.2', t['campaign']['trace_rule_ids'])
            self.assertIn('r-it marker', oracle_issue(t))
            for ops in [['yaNluk'], ['Ric', 'yaNluk'], ['Ric']]:
                t['derivation']['sanadi'] = ops
                self.assertIsNone(oracle_issue(t))
        t = make_task(entries['02.0070'], 'development', dict(self.four['morphology'], lakara='Lun'),
                      'causative_of_intensive_luk', ['yaNluk', 'Ric'])
        self.assertIn('7.4.2', t['campaign']['trace_rule_ids'])
        self.assertIsNone(oracle_issue(t))

    def test_luk_lexical_mit_quarantine_preserves_am_final_prescription(self):
        entries = {e.code: e for e in load_entries()}
        for code, excluded in [('01.0870', True), ('01.0867', True),
                               ('04.0101', False), ('01.0542', False)]:
            t = make_task(entries[code], 'development', self.four['morphology'],
                          'causative_of_intensive_luk', ['yaNluk', 'Ric'])
            self.assertIn('6.4.92', t['campaign']['trace_rule_ids'])
            issue = oracle_issue(t)
            if excluded:
                self.assertIn('lexical mit', issue)
                t['derivation']['sanadi'] = ['Ric']
                self.assertIsNone(oracle_issue(t))
            else:
                self.assertIsNone(issue)

    def test_luk_shtip_rule_does_not_quarantine_ordinary_causative(self):
        entry = next(e for e in load_entries() if e.code == '01.0288')
        m = dict(self.four['morphology'], lakara='Lun')
        t = make_task(entry, 'development', m, 'causative_of_intensive_luk', ['yaNluk', 'Ric'])
        self.assertIn('7.4.96', t['campaign']['trace_rule_ids'])
        self.assertIn('shtip-designated', oracle_issue(t))
        ordinary = make_task(entry, 'development', m, 'causative', ['Ric'])
        self.assertIn('7.4.96', ordinary['campaign']['trace_rule_ids'])
        self.assertIsNone(oracle_issue(ordinary))
        t['derivation']['sanadi'] = ['yaNluk']
        self.assertIsNone(oracle_issue(t))

    def test_vocalic_l_spelling_gate_preserves_other_klrp_forms(self):
        entry = next(e for e in load_entries() if e.code == '01.0866')
        t = make_task(entry, 'development', dict(self.four['morphology'], lakara='Lot',
                      purusha='Madhyama', vacana='Dvi'), 'causative_of_intensive', ['yaN', 'Ric'])
        self.assertIn('vocalic-l spelling', oracle_issue(t))
        aorist = make_task(entry, 'development', dict(self.four['morphology'], lakara='Lun',
                           purusha='Uttama', vacana='Bahu'),
                           'causative_of_intensive_luk', ['yaNluk', 'Ric'])
        self.assertIsNone(oracle_issue(aorist))
        t['campaign']['trace_rule_ids'] = []
        self.assertIsNone(oracle_issue(t))

    def test_vrasc_luk_source_gate_preserves_ordinary_intensive(self):
        entry = next(e for e in load_entries() if e.code == '06.0012')
        for ops in [['yaNluk'], ['yaNluk', 'Ric']]:
            t = make_task(entry, 'development', self.four['morphology'], 'control', ops)
            self.assertIn('vrasc intensive-luk', oracle_issue(t))
        ordinary = make_task(entry, 'development', self.four['morphology'], 'control', ['yaN'])
        self.assertIn('varIvfScyate', ordinary['gold_slp1'])
        self.assertIsNone(oracle_issue(ordinary))

    def test_prcch_luk_source_gate_preserves_ordinary_intensive(self):
        entry = next(e for e in load_entries() if e.code == '06.0149')
        for ops in [['yaNluk'], ['yaNluk', 'Ric']]:
            t = make_task(entry, 'test', self.four['morphology'], 'control', ops)
            self.assertIn('prcch intensive-luk', oracle_issue(t))
        ordinary = make_task(entry, 'test', self.four['morphology'], 'control', ['yaN'])
        self.assertIn('parIpfcCyate', ordinary['gold_slp1'])
        self.assertIsNone(oracle_issue(ordinary))

    def test_adadi_vedic_scope_preserves_classically_attested_vash(self):
        entries = {e.code: e for e in load_entries()}
        for n in range(71, 75):
            self.assertIn('Vedic-only Adadi', entry_scope_issue(entries[f'02.{n:04d}']))
        self.assertIsNone(entry_scope_issue(entries['02.0075']))

    def test_single_san_quarantines_preserve_other_tenses_and_recipes(self):
        entries = {e.code: e for e in load_entries()}
        cases = [('01.0262', 'Lrt', 'Lat', 'aj substitution'),
                 ('04.0160', 'Lun', 'Lrt', 'rdh vowel'),
                 ('02.0067', 'Lat', None, 'jagr desiderative')]
        for code, bad, good, message in cases:
            with self.subTest(code=code):
                task = make_task(entries[code], 'test', dict(self.four['morphology'], lakara=bad),
                                 'desiderative', ['san'])
                self.assertIn(message, oracle_issue(task))
                for ops in [[], ['Ric'], ['san', 'Ric']]:
                    task['derivation']['sanadi'] = ops
                    self.assertIsNone(oracle_issue(task))
                if good:
                    control = make_task(entries[code], 'test', dict(self.four['morphology'], lakara=good),
                                        'desiderative', ['san'])
                    self.assertIsNone(oracle_issue(control))

    def test_nested_ittva_gate_preserves_ordinary_causative(self):
        entry = next(e for e in load_entries() if e.code == '01.1090')
        m = dict(self.four['morphology'], lakara='Lun')
        nested = make_task(entry, 'test', m, 'causative_of_intensive_luk', ['yaNluk', 'Ric'])
        self.assertIn('7.4.81', nested['campaign']['trace_rule_ids'])
        self.assertIn('nested intensive', oracle_issue(nested))
        ordinary = make_task(entry, 'test', m, 'causative', ['Ric'])
        self.assertIn('7.4.81', ordinary['campaign']['trace_rule_ids'])
        self.assertIsNone(oracle_issue(ordinary))

    def test_guh_guna_condition_preserves_luk_and_ordinary_causative(self):
        entry = next(e for e in load_entries() if e.code == '01.1043')
        for ops, excluded in [(['yaN', 'Ric'], True), (['yaNluk', 'Ric'], False),
                              (['Ric'], False), (['yaN'], False)]:
            t = make_task(entry, 'test', self.four['morphology'], 'control', ops)
            issue = oracle_issue(t)
            if excluded:
                self.assertIn('guh lengthening', issue)
            else:
                self.assertIsNone(issue)

    def test_bru_timing_hold_is_specific_to_causative_of_intensive_luk(self):
        entry = next(e for e in load_entries() if e.code == '02.0039')
        for lakara in ['Lat', 'Lrt']:
            m = dict(self.four['morphology'], lakara=lakara)
            t = make_task(entry, 'test', m, 'control', ['yaNluk', 'Ric'])
            self.assertIn('bru substitution timing', oracle_issue(t))
            for ops in [['Ric'], ['yaN', 'Ric'], ['yaNluk']]:
                t = make_task(entry, 'test', m, 'control', ops)
                self.assertIsNone(oracle_issue(t))

    def test_ayadi_optional_branch_gate_preserves_full_unions_and_bare_forms(self):
        entries = {e.code: e for e in load_entries()}
        for code in ['01.1166', '01.0508', '01.0461', '01.0462', '01.0511', '06.0159']:
            with self.subTest(code=code):
                present = make_task(entries[code], 'development', self.four['morphology'],
                                    'desiderative', ['san'])
                self.assertIn('optional intrinsic ayadi', oracle_issue(present))
                future = make_task(entries[code], 'development', dict(self.four['morphology'], lakara='Lut'),
                                   'desiderative', ['san'])
                self.assertIn('3.1.31', future['campaign']['trace_rule_ids'])
                self.assertIsNone(oracle_issue(future))
                bare = make_task(entries[code], 'development', self.four['morphology'])
                self.assertIsNone(oracle_issue(bare))
        pan = make_task(entries['01.0507'], 'development', self.four['morphology'],
                        'desiderative', ['san'])
        self.assertEqual(pan['gold_slp1'], ['pipaRAyizati', 'pipaRizate'])
        self.assertIsNone(oracle_issue(pan))

    def test_curadi_aya_overreach_preserves_source_named_other_classes(self):
        entries = {e.code: e for e in load_entries()}
        for code in ['10.0303', '10.0304']:
            bare = make_task(entries[code], 'development', self.four['morphology'])
            self.assertIn('3.1.28', bare['campaign']['trace_rule_ids'])
            self.assertIn('Curadi speech', oracle_issue(bare))
            future = make_task(entries[code], 'development', dict(self.four['morphology'], lakara='Lut'),
                               'desiderative', ['san'])
            self.assertIn('Curadi speech', oracle_issue(future))
        for code in ['01.0462', '06.0159', '10.0302']:
            bare = make_task(entries[code], 'development', self.four['morphology'])
            self.assertIsNone(oracle_issue(bare))


if __name__ == '__main__':
    unittest.main()
