import unittest
from data.engine.evaluation import experiment_opus_wording_round2 as exp


class RoundTwoTests(unittest.TestCase):
    def test_all_fields_and_answer_rule_are_preserved(self):
        for family in exp.FAMILIES:
            prompt = (exp.ROOT / f"data/engine/prompts/v2/vp_{family}.txt").read_text()
            for variant in exp.VARIANTS:
                result = exp.transform(prompt, family, variant)
                self.assertEqual(result.split("Write ONLY the final form", 1)[1],
                                 prompt.split("Write ONLY the final form", 1)[1])

    def test_plans_total_one_hundred_and_cover_all_four_families(self):
        cases = []
        for family in exp.FAMILIES:
            for phase in exp.COUNTS:
                count = (4 if family == "tinanta" else 2) if phase == "discovery" else 5
                for _ in range(count):
                    cases.append({"case_id":str(len(cases)),"family":family,"phase":phase,
                                  "task":{"id":str(len(cases))},
                                  "current_prompt":"Write ONLY the final form\n=== Your task ===\ninput"})
        winners = dict.fromkeys(exp.FAMILIES,"compact")
        plans = {p:exp.plan_for(cases,p,winners) for p in exp.COUNTS}
        self.assertEqual({p:len(v) for p,v in plans.items()},exp.COUNTS)
        self.assertEqual(sum(map(len,plans.values())),100)
        self.assertEqual(len({r['request_key'] for plan in plans.values() for r in plan}),100)
        for plan in plans.values():
            self.assertEqual({r['family'] for r in plan},set(exp.FAMILIES))

    def test_selection_prioritizes_refusals_then_accuracy_and_keeps_current_on_ties(self):
        rows = {}
        for family in exp.FAMILIES:
            for variant in exp.VARIANTS:
                for i in range(4 if family == 'tinanta' else 2):
                    refused = family=='tinanta' and variant=='current'
                    wrong = family=='tinanta' and variant=='compact'
                    rows[str(len(rows))] = {'phase':'discovery','family':family,'variant':variant,
                        'status':'refused' if refused else 'completed','correct':False if wrong or refused else True,
                        'format_ok':not refused,'cost_usd':0,'usage':{},'error':None}
        self.assertEqual(exp.select_winners(rows),{'tinanta':'question','krdanta':'current','taddhitanta':'current','subanta':'current'})

    def test_selection_requires_full_discovery(self):
        with self.assertRaisesRegex(RuntimeError,'40'):
            exp.select_winners({})


if __name__=='__main__':
    unittest.main()
