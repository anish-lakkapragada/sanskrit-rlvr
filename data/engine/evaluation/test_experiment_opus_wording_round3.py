import string
import unittest
from data.engine.evaluation import experiment_opus_wording_round3 as e


class RoundThreeTests(unittest.TestCase):
    def test_templates_preserve_all_hydration_fields(self):
        fields=lambda s:sorted(x for _,x,_,_ in string.Formatter().parse(s) if x)
        for family in e.FAMILIES:
            text=(e.CANDIDATES/f'vp_{family}.txt').read_text()
            for variant in set(e.VARIANTS+e.LAYOUTS):
                rewritten=e.transform(text,family,variant)
                self.assertEqual(fields(text),fields(rewritten))
                self.assertIn('<answer>',rewritten)
                self.assertIn('</answer>',rewritten)
                self.assertIn('Devanagari',rewritten)

    def test_literal_sanskrit_inputs_survive_every_rewrite(self):
        text='Form the requested word.\n\nWrite ONLY the final form\n=== Your task ===\npratipadika (nominal base): लोडन\nbase interpretation: source gender: neuter; basic stem\ntaddhita (technical affix): थाल् (SLP1: TAl)\nartha (meaning): unrestricted\n'
        for variant in set(e.VARIANTS+e.LAYOUTS):
            result=e.transform(text,'taddhitanta',variant)
            for value in ('लोडन','थाल्','TAl'):
                self.assertIn(value,result)

    def test_plan_counts_and_repeated_requests_remain_distinct(self):
        cases=[]
        for stage in e.STAGES:
            for f in e.FAMILIES:
                n=(5 if f=='taddhitanta' else 1) if stage in ('discovery','validation') else 5
                for _ in range(n):
                    cases.append({'case_id':str(len(cases)),'phase':stage,'family':f,'task':{'id':'repeated'},
                                  'current_prompt':'Write ONLY the final form\n=== Your task ===\npratipadika (nominal base): राम\nbase interpretation: basic masculine stem\ntaddhita (technical affix): थाल् (SLP1: TAl)\nartha (meaning): unrestricted\n'})
        plans=[e.make_plan(cases,s,dict.fromkeys(e.FAMILIES,'current')) for s in e.STAGES]
        self.assertEqual([len(p) for p in plans],[40,40,20])
        self.assertEqual(len({p['request_key'] for plan in plans for p in plan}),100)

    def test_repeated_hard_refusals_are_not_hidden_by_easy_successes(self):
        rows={};cases=[]
        for f in e.FAMILIES:
            for v in e.VARIANTS:
                cid=str(len(cases));cases.append({'case_id':cid,'task':{'id':e.HARD if f=='taddhitanta' else f}})
                refused=f=='taddhitanta' and v=='current'
                rows[cid]={'case_id':cid,'family':f,'variant':v,'phase':'discovery','status':'refused' if refused else 'completed',
                           'correct':not refused,'format_ok':not refused,'cost_usd':0,'usage':{},'error':None}
        self.assertEqual(e.choose(rows,cases),{'tinanta':'current','krdanta':'current','taddhitanta':'positive_format','subanta':'current'})


if __name__=='__main__':unittest.main()
