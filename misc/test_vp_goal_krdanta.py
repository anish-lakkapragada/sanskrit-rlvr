"""Nominal derivation integrity and the declared grammatical scope."""
import copy
import unittest
from misc import vp_compositional as g
from misc.vp_goal_krdanta import task_for, validate_task


class KrdantaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entry = next(e for e in g.old.load_entries() if e.code=='01.0001')

    def test_generation_and_feminine_inflection(self):
        t=task_for(self.entry,'development','causative',[],'Satf','Stri','Trtiya','Eka')
        self.assertIn('BAvayantyA',t['gold_slp1'])
        validate_task(t,self.entry,'development')

    def test_corrupted_gold_and_missing_gender_cannot_pass(self):
        t=task_for(self.entry,'development','causative',[],'Satf','Stri','Trtiya','Eka')
        bad=copy.deepcopy(t);bad['gold_slp1']=['wrong']
        with self.assertRaises(ValueError):validate_task(bad,self.entry,'development')
        bad=copy.deepcopy(t);bad['morphology']['linga']='Pum'
        with self.assertRaises(ValueError):validate_task(bad,self.entry,'development')

    def test_unreviewed_suffix_and_participle_context_rejected(self):
        with self.assertRaises(ValueError):task_for(self.entry,'development','causative',[],'kvasu','Pum','Trtiya','Eka')
        with self.assertRaises(ValueError):task_for(self.entry,'development','causative',[],'Satf','Pum','Prathama','Eka')


if __name__=='__main__':unittest.main()
