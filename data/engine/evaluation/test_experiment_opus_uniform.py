"""Offline checks for the new paid-request admission and task preservation."""
from copy import deepcopy
import unittest

from data.engine.evaluation import experiment_opus_uniform as e


class UniformTests(unittest.TestCase):
    def test_budget_reserves_full_output_before_admission(self):
        m = {'pricing': {'rates_usd_per_million_tokens': {'uncached_input': 4, 'cache_write_input': 8, 'output': 20}}}
        bound = e.reserve('Sanskrit राम', m)
        self.assertGreater(bound, 2.56)
        self.assertTrue(e.can_admit(0, 0, bound))
        self.assertFalse(e.can_admit(0, bound, bound))
        self.assertFalse(e.can_admit(2.5, 0, bound))
        self.assertFalse(e.can_admit(0, 3, bound))
        self.assertEqual(e.opus.request_body('test')['max_tokens'], 128000)

    def test_rewrites_keep_all_placeholders_and_answer_rule(self):
        answer = None
        for f in e.FAMILIES:
            original = (e.ROOT / f'data/engine/prompts/v2/vp_{f}.txt').read_text()
            rule = original.split('Write ONLY the final form', 1)[1].split('=== Your task ===')[0]
            if answer is None:
                answer = rule
            self.assertEqual(rule, answer)
            for v in e.VARIANTS:
                rewritten = e.transform(original, f, v)
                self.assertEqual(e.fields(original), e.fields(rewritten))
                self.assertIn('Write ONLY the final form' + rule, rewritten)
                if v not in ('shared_sentences',):
                    self.assertEqual(original.split('=== Your task ===')[1], rewritten.split('=== Your task ===')[1])

    def test_gold_never_enters_rendering_and_optional_inputs_survive(self):
        # Existing recorded tasks include the troublesome Sanskrit inputs.
        cases = e.read_json(e.common.FOLDER / 'cases.json')
        for c in cases:
            f, task = c['family'], c['task']
            original = (e.ROOT / f'data/engine/prompts/v2/vp_{f}.txt').read_text()
            changed = deepcopy(task)
            changed['gold_devanagari'] = ['THIS MUST NOT ENTER THE PROMPT']
            for v in e.VARIANTS:
                template = e.transform(original, f, v)
                prompt = e.render(template, f, task)
                self.assertEqual(prompt, e.render(template, f, changed))
                for name in e.fields(original):
                    self.assertNotIn('{' + name + '}', prompt)


if __name__ == '__main__':
    unittest.main()
