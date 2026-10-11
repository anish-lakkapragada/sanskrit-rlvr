import unittest
from misc.vp_goal_dataset import exact_reward, score


class DatasetTests(unittest.TestCase):
    def test_reward_matches_final_answer_protocol(self):
        self.assertEqual(exact_reward("<answer>  भवति </answer>", ["भवति"]), 1)
        self.assertEqual(exact_reward("<answer>भवतः</answer>", ["भवति", "भवतः"]), 1)
        self.assertEqual(exact_reward("<answer>भवति</answer><answer>भवति</answer>", ["भवति"]), 0)
        self.assertEqual(exact_reward("भवति", ["भवति"]), 0)
        self.assertEqual(exact_reward(None, ["भवति"]), 0)

    def test_missing_or_duplicate_completions_cannot_inflate_score(self):
        tasks = [{"id": "a", "gold_devanagari": ["भवति"]}, {"id": "b", "gold_devanagari": ["भवतः"]}]
        a = {"id": "a", "completion": "<answer>भवति</answer>"}
        with self.assertRaises(ValueError):
            score(tasks, [a])
        with self.assertRaises(ValueError):
            score(tasks, [a, a])
        result = score(tasks, [a, {"id": "b", "completion": ""}])
        self.assertEqual(result["accuracy"], 0.5)


if __name__ == "__main__":
    unittest.main()
