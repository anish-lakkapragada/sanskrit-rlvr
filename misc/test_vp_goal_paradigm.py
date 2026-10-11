"""Verifier integrity: partial correctness, alternatives and malformed answers."""
import unittest
from misc.vp_goal_paradigm import grade
from misc.vp_goal_dataset import task_reward


class ParadigmVerifierTests(unittest.TestCase):
    def setUp(self):
        self.task = {'task_type':'finite_paradigm', 'forms':[
            {'gold_devanagari':['भवति']}, {'gold_devanagari':['भवन्ति','भवन्ति ']}]}

    def test_all_forms_and_alternatives(self):
        text = '<answer>{"2":" भवन्ति ","1":"भवति"}</answer>'
        self.assertTrue(grade(self.task, text)['is_correct'])
        self.assertEqual(task_reward(text, self.task), 1)

    def test_partial_answer_is_not_whole_task_success(self):
        r = grade(self.task, '<answer>{"1":"भवति","2":"भवतः"}</answer>')
        self.assertEqual(r['correct_forms'], 1)
        self.assertFalse(r['is_correct'])

    def test_missing_extra_duplicate_or_non_string_rows_fail(self):
        for value in ['{"1":"भवति"}', '{"1":"भवति","2":"भवन्ति","3":"भवति"}',
                      '{"1":"wrong","1":"भवति","2":"भवन्ति"}',
                      '{"1":"भवति","2":["भवन्ति"]}', 'null']:
            self.assertFalse(grade(self.task, '<answer>'+value+'</answer>')['format_valid'])

    def test_multiple_answer_blocks_fail(self):
        self.assertFalse(grade(self.task, '<answer>{}</answer><answer>{}</answer>')['is_correct'])

    def test_line_format_requires_every_form_in_order(self):
        self.task['prompt_version'] = 'paradigm-v4-lines'
        text = '<answer>भवति\nभवन्ति</answer>'
        self.assertTrue(grade(self.task, text)['is_correct'])
        self.assertEqual(task_reward(text, self.task), 1)
        self.assertFalse(grade(self.task, '<answer>भवन्ति\nभवति</answer>')['is_correct'])
        self.assertFalse(grade(self.task, '<answer>भवति</answer>')['format_valid'])
        self.assertFalse(grade(self.task, '<answer>भवति\nभवन्ति\nभवति</answer>')['format_valid'])
        self.assertFalse(grade(self.task, '<answer>भवति</answer><answer>भवन्ति</answer>')['is_correct'])


if __name__ == '__main__':
    unittest.main()
