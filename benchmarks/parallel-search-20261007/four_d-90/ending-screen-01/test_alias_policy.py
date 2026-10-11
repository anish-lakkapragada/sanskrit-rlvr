"""Offline adversarial checks of the frozen-list grading contract."""
import copy
import json
import unittest
from pathlib import Path
from alias_policy import grade_policy, validate_policy, sites

OUT=Path(__file__).resolve().parent

class AliasPolicyChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks=json.loads((OUT/'proposedtasks.json').read_text())
        cls.policy=json.loads((OUT/'alias-policy.json').read_text())
        cls.items=validate_policy(cls.policy,cls.tasks)

    def test_every_canonical_and_alias(self):
        for item in self.items.values():
            for form in item['canonical_forms_devanagari']:
                result=grade_policy('<answer>'+form+'</answer>',item['task_id'],self.policy)
                self.assertTrue(result['canonical_correct']);self.assertTrue(result['alias_aware_correct'])
                self.assertFalse(result['requires_source_adjudication'])
            for form in item['aliases_devanagari']:
                result=grade_policy('<answer>'+form+'</answer>',item['task_id'],self.policy)
                self.assertFalse(result['canonical_correct']);self.assertTrue(result['alias_aware_correct'])
                self.assertFalse(result['requires_source_adjudication'])

    def test_only_existing_benchmark_extraction(self):
        item=next(iter(self.items.values()));form=item['canonical_forms_devanagari'][0]
        for text in [form,'<answer></answer>','<answer>'+form,
                     '<answer>'+form+'</answer><answer>भवति</answer>']:
            result=grade_policy(text,item['task_id'],self.policy)
            self.assertIsNone(result['answer']);self.assertFalse(result['alias_aware_correct'])
        for text in ['<answer>गलत</answer>','<answer>'+form+' भवति</answer>']:
            result=grade_policy(text,item['task_id'],self.policy)
            self.assertFalse(result['alias_aware_correct']);self.assertTrue(result['requires_source_adjudication'])
        result=grade_policy('prose <answer> '+form+' </answer> prose',item['task_id'],self.policy)
        self.assertTrue(result['canonical_correct']) # same existing extractor, no new format rule

    def test_task_binding_and_no_general_collapse(self):
        for task in self.tasks:
            item=self.items[task['id']]
            elsewhere=next(x for x in self.policy['items'] if x['task_id']!=task['id']
                and x['canonical_forms_devanagari'][0] not in item['canonical_forms_devanagari']+item['aliases_devanagari'])
            self.assertFalse(grade_policy('<answer>'+elsewhere['canonical_forms_devanagari'][0]+'</answer>',
                task['id'],self.policy)['alias_aware_correct'])
        with self.assertRaises(ValueError):grade_policy('<answer>भवति</answer>','unknown',self.policy)
        # Triple final stops are not accepted by an unrestricted collapse rule.
        item=next(x for x in self.policy['items'] if 'alUzIt' in x['canonical_forms_slp1'])
        self.assertIn('alUzItt',item['aliases_slp1']);self.assertNotIn('alUzIttt',item['aliases_slp1'])

    def test_membership_key_and_transliteration_tampering(self):
        for change in ['missing','reordered','key','alias']:
            p=copy.deepcopy(self.policy)
            if change=='missing':p['items'].pop()
            elif change=='reordered':p['items'].reverse()
            elif change=='key':p['items'][0]['canonical_forms_devanagari']=['भवति']
            else:next(x for x in p['items'] if x['aliases_devanagari'])['aliases_devanagari'][0]='भवति'
            with self.assertRaises(ValueError):validate_policy(p,self.tasks)

    def test_licensed_sites_and_combinations(self):
        item=next(x for x in self.policy['items'] if 'anardIt' in x['canonical_forms_slp1'])
        for form in ['anardItt','anarddIt','anarddItt','anarddIdd']:
            self.assertIn(form,item['aliases_slp1'])
        for form in ['anarrdIt','anArdIt','anardddIt']:
            self.assertNotIn(form,item['aliases_slp1'])
        self.assertEqual(sites('karzati')[0],[]) # sar before vowel, no doubled r
        self.assertEqual(sites('barhati')[0],[]) # h not yar, no doubled r
        self.assertTrue(sites('cuwwa')[1]) # no silent triple closure
        s,_=sites('tuPyAsuH');self.assertEqual(s[0]['replacement'],'pP')
        s,_=sites('stuByAsuH');self.assertEqual(s[0]['replacement'],'bB')

if __name__=='__main__':unittest.main()
